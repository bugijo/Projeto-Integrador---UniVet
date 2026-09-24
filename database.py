"""DB-API comum; SQL de negócio permanece explícito e parametrizado.

O adaptador só ajusta bind markers e RETURNING de tabelas conhecidas;
nunca converte PRAGMA, funções de data, DDL ou transações SQLite em SQL PG.
"""
from datetime import date, datetime
from decimal import Decimal
import os
import re
import sqlite3
import threading
from urllib.parse import urlsplit

import psycopg
from psycopg_pool import ConnectionPool

sqlite3.register_adapter(Decimal, str)
INTEGRITY_ERRORS = (sqlite3.IntegrityError, psycopg.IntegrityError)
DATABASE_ERRORS = (sqlite3.Error, psycopg.Error)
ID_TABLES = frozenset(('usuarios','tutores','especies','racas','veterinarios','servicos',
    'pets','consultas','condicoes_clinicas','historico_alteracoes','categorias',
    'fornecedores','produtos','lotes','movimentacoes_estoque','itens_consulta','security_events'))
_pools = {}
_pool_lock = threading.Lock()


def is_postgres(target):
    if not isinstance(target, str):
        return False
    scheme = urlsplit(target).scheme
    return scheme in ('postgres', 'postgresql') or scheme.startswith(('postgres+', 'postgresql+'))


def bind_markers(statement):
    # Literais/identificadores SQL preservados; nenhum valor de usuário entra aqui.
    # Compatibilidade pontual para a expressão de data usada pelo legado SQLite
    # em fixtures e no fechamento automático de consultas.
    statement = re.sub(
        r"replace\(substr\(datetime\(([^,()]+),\s*'\+'\s*\|\|\s*([^ ]+)\s*\|\|\s*' minutes'\),\s*1,\s*16\),\s*' ',\s*'T'\)",
        r"(\1)::timestamp + (\2 || ' minutes')::interval",
        statement,
        flags=re.I,
    )
    tokens = re.split(r"('(?:''|[^'])*'|\"(?:\"\"|[^\"])*\"|--[^\n]*|/\*.*?\*/)", statement, flags=re.S)
    return ''.join(t.replace('%','%%') if i % 2 else t.replace('%','%%').replace('?', '%s') for i,t in enumerate(tokens))


class Row(dict):
    def __getitem__(self, key):
        return tuple(self.values())[key] if isinstance(key, (int,slice)) else super().__getitem__(key)

    def __iter__(self):
        return iter(self.values())


def row_factory(cursor):
    names = [column.name for column in cursor.description] if cursor.description else []
    def row(values):
        # Contrato legado: consultas clínicas trabalham com precisão de minuto.
        # SQLite já devolve esse formato textual; normalizamos o timestamp PG
        # para evitar que o sufixo ``:00`` quebre os parsers existentes.
        normalized = []
        for value in values:
            if isinstance(value, datetime):
                value = value.isoformat(timespec='minutes')
            elif isinstance(value, date):
                value = value.isoformat()
            normalized.append(value)
        return Row(zip(names, normalized))
    return row


class Cursor:
    def __init__(self, cursor, lastrowid=None):
        self.cursor = cursor
        self.lastrowid = lastrowid

    @property
    def rowcount(self):
        return self.cursor.rowcount

    def fetchone(self):
        return self.cursor.fetchone()

    def fetchall(self):
        return self.cursor.fetchall()

    def __iter__(self):
        return iter(self.cursor)


class PostgresConnection:
    dialect = 'postgresql'

    def __init__(self, pool):
        self.pool = pool
        self.raw = pool.getconn(timeout=5)
        self.closed = False
        self.last_insert_id = None
        self._write_started = False

    def execute(self, statement, params=()):
        if re.fullmatch(r"\s*SELECT\s+last_insert_rowid\(\)\s*;?\s*", statement, re.I):
            cursor = self.raw.execute('SELECT %s', (self.last_insert_id,))
            self._cursor = Cursor(cursor, self.last_insert_id)
            return self._cursor
        match = re.match(r'\s*INSERT\s+INTO\s+(\w+)\b', statement, re.I)
        generated = bool(match and match[1].lower() in ID_TABLES and not re.search(r'\bRETURNING\b',statement,re.I))
        if generated:
            statement = statement.rstrip().rstrip(';') + ' RETURNING id'
        cursor = self.raw.execute(bind_markers(statement), params)
        identifier = None
        if generated:
            row = cursor.fetchone()
            identifier = row[0] if row else None
            self.last_insert_id = identifier
        self._cursor = Cursor(cursor,identifier)
        return self._cursor

    def fetchone(self):
        return self._cursor.fetchone()

    def fetchall(self):
        return self._cursor.fetchall()

    def __iter__(self):
        return iter(self._cursor)

    @property
    def in_transaction(self):
        # O psycopg abre transação também para um SELECT. O contrato legado do
        # app considera transação relevante a partir do lock de escrita.
        return self._write_started

    @property
    def lastrowid(self):
        return self.last_insert_id

    def commit(self):
        self.raw.commit()
        self._write_started = False

    def rollback(self):
        self.raw.rollback()
        self._write_started = False

    def close(self):
        if not self.closed:
            self.closed = True
            self.raw.rollback()
            self.pool.putconn(self.raw)

    def __enter__(self):
        return self

    def __exit__(self, kind, value, traceback):
        try:
            if kind:
                self.rollback()
            else:
                self.commit()
        finally:
            self.close()


def connect(target, pool_size=4):
    if not is_postgres(target):
        conn = sqlite3.connect(target,timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA foreign_keys=ON')
        return conn
    if not 1 <= pool_size <= 16:
        raise ValueError('Limite de conexões inválido.')
    key = (os.getpid(), target, pool_size)
    with _pool_lock:
        if key not in _pools:
            _pools[key] = ConnectionPool(target, min_size=0,max_size=pool_size,timeout=5,
                kwargs={'row_factory':row_factory,'prepare_threshold':None,'connect_timeout':5,
                        'options':'-c statement_timeout=10000 -c lock_timeout=5000 -c idle_in_transaction_session_timeout=15000 -c timezone=America/Sao_Paulo'},
                open=True)
        pool = _pools[key]
    return PostgresConnection(pool)


def close_pools():
    with _pool_lock:
        for pool in _pools.values():
            pool.close()
        _pools.clear()


def begin_write(connection):
    if getattr(connection,'dialect',None) == 'postgresql':
        # Serialização conservadora de operações críticas, equivalente ao modelo
        # SQLite, mas só no domínio clínico/estoque; sessões/leitura não aguardam.
        # Lock transacional funciona também em poolers por transação.
        connection.execute('SELECT pg_advisory_xact_lock(734120, 1)')
        connection._write_started = True
    else:
        connection.execute('BEGIN IMMEDIATE')


def last_insert_id(connection):
    if getattr(connection,'dialect',None) == 'postgresql':
        return connection.last_insert_id
    return connection.execute('SELECT last_insert_rowid()').fetchone()[0]
