"""Caracterização defensiva local, não uma suíte de aprovação de segurança.

Executar na raiz: PYTHONPATH=.:tests .venv/bin/python docs/audit_local.py
Saída JSON redigida; nenhuma conexão a produção. Banco sempre temporário.
"""
import ast
from concurrent.futures import ThreadPoolExecutor
from contextlib import redirect_stdout
import io
import json
import math
from pathlib import Path
import platform
import sqlite3
import statistics
import threading
import time

import app as web
import init_db
from estoque import services
from test_app import UniVetAppTests
from test_estoque import EstoqueServicesTests


def http_checks():
    fixture = UniVetAppTests()
    with redirect_stdout(io.StringIO()):
        fixture.setUp()
    result = {}
    try:
        client = fixture.client
        routes = []
        for node in ast.walk(ast.parse(Path('app.py').read_text())):
            if isinstance(node, ast.FunctionDef):
                for dec in node.decorator_list:
                    if isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute) and dec.func.attr == 'route':
                        routes.append({'route': ast.literal_eval(dec.args[0]), 'line': node.lineno,
                                       'guarded': any(isinstance(d, ast.Name) and d.id == 'login_obrigatorio' for d in node.decorator_list)})
        result['routes'] = routes
        result['anonymous'] = {p: client.get(p).status_code for p in ['/estoque', '/api/estoque/produtos', '/pets/1/historico-clinico', '/estoque/exportar/posicao.csv']}
        result['sql_login_bypass'] = client.post('/login', data={'login': "' OR 1=1 --", 'senha': 'invalid'}).status_code
        with client.session_transaction() as sess:
            result['sql_login_authenticated'] = 'usuario_id' in sess
        login, _, _, password = init_db.USUARIOS_PADRAO[0]
        response = client.post('/login', data={'login': login, 'senha': password})
        cookie = response.headers.get('Set-Cookie', '')
        result['cookie_flags'] = {flag: flag.lower() in cookie.lower() for flag in ['HttpOnly', 'Secure', 'SameSite']}
        page = client.get('/estoque')
        result['headers'] = {h: page.headers.get(h) for h in ['Content-Security-Policy', 'X-Frame-Options', 'X-Content-Type-Options', 'Strict-Transport-Security', 'Cache-Control']}
        result['csrf_post'] = client.post('/estoque/categorias', data={'nome': 'AUDIT-CSRF'}, headers={'Origin': 'https://example.invalid'}).status_code
        conn = fixture._conexao()
        result['csrf_persisted'] = conn.execute("SELECT count(*) FROM categorias WHERE nome='AUDIT-CSRF'").fetchone()[0]
        conn.execute('UPDATE usuarios SET ativo=0 WHERE login=?', (login,))
        conn.commit()
        result['deactivated_session_status'] = client.get('/api/estoque/resumo').status_code
        conn.execute('UPDATE usuarios SET ativo=1 WHERE login=?', (login,))
        conn.commit()
        payload = '<script>alert(1)</script>'
        client.post('/estoque/categorias', data={'nome': payload})
        body = client.get('/estoque/categorias').get_data(as_text=True)
        result['stored_xss_escaped'] = payload not in body and '&lt;script&gt;' in body
        product = conn.execute("INSERT INTO produtos(nome,codigo,tipo) VALUES ('=1+1','AUDIT-CSV','Produto')").lastrowid
        conn.commit()
        result['csv_formula_unescaped'] = '=1+1;' in client.get('/estoque/exportar/posicao.csv').get_data(as_text=True)
        result['sql_search_status'] = client.get('/api/estoque/produtos', query_string={'busca': "' OR 1=1 --"}).status_code
        client.post('/estoque/produtos/novo', data={'nome': 'AUDIT-INF', 'tipo': 'Produto', 'codigo': 'AUDIT-INF', 'estoque_minimo': 'inf', 'margem_lucro_percentual': '30'})
        value = conn.execute("SELECT estoque_minimo FROM produtos WHERE codigo='AUDIT-INF'").fetchone()
        result['infinite_minimum_accepted'] = bool(value and math.isinf(value[0]))
        conn.execute('DELETE FROM produtos WHERE id=? OR codigo=?', (product, 'AUDIT-INF'))
        conn.commit()
        client.get('/logout')
        login2, _, _, password2 = init_db.USUARIOS_PADRAO[1]
        client.post('/login', data={'login': login2, 'senha': password2})
        result['vet_can_write_catalog'] = client.post('/estoque/categorias', data={'nome': 'AUDIT-VET'}).status_code
        result['vet_write_persisted'] = conn.execute("SELECT count(*) FROM categorias WHERE nome='AUDIT-VET'").fetchone()[0]
        timings = []
        statuses = []
        for _ in range(30):
            start = time.perf_counter()
            statuses.append(client.get('/api/estoque/produtos').status_code)
            timings.append((time.perf_counter() - start) * 1000)
        result['local_bounded_load'] = {'requests': len(statuses), 'errors': sum(s != 200 for s in statuses), 'median_ms': round(statistics.median(timings), 2), 'p95_ms': round(sorted(timings)[28], 2), 'platform': platform.system(), 'mode': 'Flask test client sequential; demo dataset; not production capacity'}
        backup_path = Path(fixture.temp_dir.name) / 'backup.db'
        with sqlite3.connect(backup_path) as backup:
            conn.backup(backup)
        with sqlite3.connect(backup_path) as restored:
            result['backup_restore'] = {'integrity': restored.execute('PRAGMA integrity_check').fetchone()[0], 'foreign_key_errors': len(restored.execute('PRAGMA foreign_key_check').fetchall()), 'same_products': restored.execute('SELECT count(*) FROM produtos').fetchone()[0] == conn.execute('SELECT count(*) FROM produtos').fetchone()[0]}
        conn.execute("INSERT INTO usuarios(login,senha_hash,nome,perfil,ativo) VALUES ('audit-extra','not-a-real-hash','Ficticio','admin',1)")
        conn.execute('UPDATE usuarios SET senha_hash=? WHERE login=?', ('changed-hash-for-audit', login))
        conn.commit()
        with redirect_stdout(io.StringIO()):
            init_db.init_db()
        result['init_deletes_extra_user'] = conn.execute("SELECT count(*) FROM usuarios WHERE login='audit-extra'").fetchone()[0] == 0
        result['init_resets_password'] = conn.execute('SELECT senha_hash FROM usuarios WHERE login=?', (login,)).fetchone()[0] != 'changed-hash-for-audit'
        conn.close()
    finally:
        fixture.tearDown()
    return result


class SyncedCursor:
    def __init__(self, cursor, barrier):
        self.cursor, self.barrier = cursor, barrier

    def fetchone(self):
        row = self.cursor.fetchone()
        self.barrier.wait(timeout=10)
        return row


class SyncedConnection:
    """Force a legal interleaving after the existing unprotected read."""
    def __init__(self, conn, barrier, marker):
        self.conn, self.barrier, self.marker = conn, barrier, marker

    def execute(self, sql, args=()):
        cursor = self.conn.execute(sql, args)
        if self.marker in sql:
            return SyncedCursor(cursor, self.barrier)
        return cursor

    def __getattr__(self, name):
        return getattr(self.conn, name)


def concurrency_check(mode):
    fixture = EstoqueServicesTests()
    fixture.setUp()
    try:
        lot, _ = fixture.entrada('AUDIT', 10, None)
        movement = None
        if mode == 'estorno':
            movement = services.registrar_saida_fefo(fixture.connection, fixture.produto_id, 3, 1)[0]['movimentacao_id']
        path = fixture.connection.execute('PRAGMA database_list').fetchone()[2]
        barrier = threading.Barrier(2)
        def worker(index):
            conn = sqlite3.connect(path, timeout=10)
            conn.row_factory = sqlite3.Row
            conn.execute('PRAGMA foreign_keys=ON')
            try:
                if mode == 'saida':
                    barrier.wait(timeout=10)
                    services.registrar_saida_fefo(conn, fixture.produto_id, 7, 1)
                elif mode == 'estorno':
                    proxy = SyncedConnection(conn, barrier, "SELECT 1 FROM movimentacoes_estoque")
                    services.registrar_estorno(proxy, movement, 1)
                else:
                    proxy = SyncedConnection(conn, barrier, 'SELECT * FROM lotes WHERE id = ?')
                    services.registrar_ajuste(proxy, lot, 12 + index, 1, 'Audit')
                return 'ok'
            except services.EstoqueError as error:
                return type(error).__name__
            finally:
                conn.close()
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(worker, [0, 1]))
        balance = fixture.saldo()
        ledger = fixture.connection.execute('SELECT sum(quantidade_variacao) FROM movimentacoes_estoque').fetchone()[0]
        return {'results': results, 'balance': balance, 'ledger': ledger, 'consistent': balance == ledger, 'reversals': fixture.connection.execute("SELECT count(*) FROM movimentacoes_estoque WHERE tipo='Estorno'").fetchone()[0]}
    finally:
        fixture.tearDown()


if __name__ == '__main__':
    raise SystemExit('Reprodução histórica arquivada. Use unittest discover -s tests -v; as barreiras antigas não são compatíveis com os locks corrigidos.')
