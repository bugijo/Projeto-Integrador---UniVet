"""Backup PostgreSQL e restore em destino vazio, sem URL/senha nos argumentos.

Usa ferramentas PostgreSQL locais ou cliente Docker gratuito, sem volumes.
Somente dumps confiáveis do projeto; restore não remove dados existentes.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from urllib.parse import urlsplit, unquote, parse_qs
import psycopg
from psycopg import sql
from config import database_target, load_settings
from database import is_postgres


def client(command, database, stdin=None, stdout=None):
    if not is_postgres(database_target(database)):
        raise ValueError('PostgreSQL obrigatório.')
    parsed=urlsplit(database)
    env=dict(os.environ, PGHOST=parsed.hostname, PGPORT=str(parsed.port or 5432),
        PGUSER=unquote(parsed.username), PGPASSWORD=unquote(parsed.password or ''),
        PGDATABASE=unquote(parsed.path[1:]), PGCONNECT_TIMEOUT='10')
    for key in ('PGSERVICE','PGSERVICEFILE','PGOPTIONS','PGPASSFILE','PGSSLMODE','PGSSLROOTCERT','PGCHANNELBINDING'):
        env.pop(key,None)
    mapping={'sslmode':'PGSSLMODE','sslrootcert':'PGSSLROOTCERT','channel_binding':'PGCHANNELBINDING'}
    query=parse_qs(parsed.query)
    for key, target in mapping.items():
        if key in query:
            env[target]=query[key][0]
    executable=shutil.which(command[0])
    if executable:
        argv=[executable,*command[1:]]
    else:
        if 'sslrootcert' in query:
            raise ValueError('CA privada exige cliente PostgreSQL local; não montar diretórios de credenciais automaticamente.')
        argv=['docker','run','--rm','-i','--network','host']
        for key in ('PGHOST','PGPORT','PGUSER','PGPASSWORD','PGDATABASE','PGCONNECT_TIMEOUT','PGSSLMODE','PGCHANNELBINDING'):
            if key in env:
                argv.extend(['-e',key])
        argv.extend(['postgres:16-alpine',*command])
    result=subprocess.run(argv,env=env,stdin=stdin,stdout=stdout or subprocess.PIPE,
        stderr=subprocess.PIPE,timeout=180)
    if result.returncode:
        raise RuntimeError('Cliente PostgreSQL recusou a operação; conteúdo sensível não foi registrado.')
    return result


def backup(database,destination):
    destination=Path(destination).absolute()
    if destination.exists() or destination.is_symlink():
        raise ValueError('Destino precisa ser novo.')
    with tempfile.TemporaryDirectory(prefix='.univet-pgdump-',dir=destination.parent) as temporary:
        staged=Path(temporary)/'dump'
        descriptor=os.open(staged,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
        with os.fdopen(descriptor,'wb') as stream:
            client(['pg_dump','--format=custom','--no-owner','--no-privileges'],database,stdout=stream)
            stream.flush()
            os.fsync(stream.fileno())
        if staged.stat().st_size==0:
            raise RuntimeError('Backup vazio.')
        digest=hashlib.file_digest(staged.open('rb'),'sha256').hexdigest()
        os.link(staged,destination)  # Não sobrescreve, inclusive em corrida.
    return {'sha256':digest,'bytes':destination.stat().st_size,'restore_validated':False}


def restore(source,target):
    # Não usa --clean nem DROP. Falha se houver qualquer tabela pública.
    with psycopg.connect(database_target(target),connect_timeout=10) as conn:
        if conn.execute("SELECT 1 FROM pg_tables WHERE schemaname='public'").fetchone():
            raise ValueError('Restore exige banco separado e vazio.')
    with Path(source).open('rb') as stream:
        client(['pg_restore','--single-transaction','--exit-on-error','--no-owner','--no-privileges','--dbname',unquote(urlsplit(target).path[1:])],target,stdin=stream)
    with psycopg.connect(target,connect_timeout=10) as conn:
        if conn.execute("SELECT 1 FROM pg_constraint WHERE NOT convalidated AND connamespace='public'::regnamespace").fetchone():
            raise RuntimeError('Constraint não validada.')
    return {'restored':True,'comparison_required':True}


def fingerprint(database):
    """Digest de todas as linhas e contagens, sem expor seus conteúdos."""
    result={}
    with psycopg.connect(database,connect_timeout=10) as conn:
        conn.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
        tables=conn.execute("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename").fetchall()
        for (table,) in tables:
            rows=conn.execute(sql.SQL('SELECT row_to_json(t)::text FROM {} t').format(sql.Identifier(table))).fetchall()
            # Ordenação canônica independente de plano/ordem física.
            canonical=sorted(json.dumps(json.loads(row[0]),sort_keys=True,ensure_ascii=False) for row in rows)
            result[table]={'rows':len(rows),'sha256':hashlib.sha256('\n'.join(canonical).encode()).hexdigest()}
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description='DATABASE_URL por ambiente. Restore somente para banco separado vazio; dumps confiáveis.')
    parser.add_argument('operation',choices=['backup','restore'])
    parser.add_argument('file',type=Path)
    args=parser.parse_args()
    try:
        target=load_settings().database
        result=backup(target,args.file) if args.operation=='backup' else restore(args.file,target)
    except Exception:
        parser.exit(1,'Operação recusada; confira cliente, ambiente, acesso e destino em canal privado.\n')
    print(json.dumps(result))
