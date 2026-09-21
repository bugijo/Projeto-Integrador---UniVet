"""POC PostgreSQL local e descartável. Não é adaptador do SQLite da aplicação.

uvx --from psycopg --with psycopg-binary python perf/postgres_poc.py
Requer Docker local; não monta arquivos e não recebe URL de banco externo.
"""
from concurrent.futures import ThreadPoolExecutor
import json
import os
import secrets
import subprocess
import time
import uuid

import psycopg


def main():
    name='univet-pg-audit-'+uuid.uuid4().hex[:12]
    password=secrets.token_hex(24)
    env=dict(os.environ,POSTGRES_PASSWORD=password)
    started=False
    try:
        subprocess.run(['docker','run','--detach','--rm','--name',name,'-e','POSTGRES_PASSWORD',
                        '-p','127.0.0.1::5432','postgres:16-alpine'],env=env,
                       check=True,capture_output=True,timeout=180)
        started=True
        address=subprocess.check_output(['docker','port',name,'5432/tcp'],text=True,timeout=10).strip()
        host,port=address.rsplit(':',1)
        assert host=='127.0.0.1'
        # DATABASE_URL apenas da instância recém-criada, jamais de os.environ.
        database_url=f'postgresql://postgres:{password}@{host}:{port}/postgres'
        for _ in range(60):
            try:
                conn=psycopg.connect(database_url,connect_timeout=2)
                break
            except psycopg.OperationalError:
                time.sleep(1)
        else:
            raise RuntimeError('PostgreSQL local não iniciou.')
        with conn:
            conn.execute('CREATE TABLE produtos(id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, nome text NOT NULL)')
            conn.execute('CREATE TABLE lotes(id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, produto_id bigint REFERENCES produtos(id), saldo numeric(14,3) NOT NULL CHECK(saldo>=0), validade date)')
            conn.execute('CREATE TABLE movimentos(id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, lote_id bigint REFERENCES lotes(id), quantidade numeric(14,3) CHECK(quantidade>0))')
            pid=conn.execute("INSERT INTO produtos(nome) VALUES ('Produto fictício') RETURNING id").fetchone()[0]
            lid=conn.execute("INSERT INTO lotes(produto_id,saldo,validade) VALUES (%s,10,'2099-01-01') RETURNING id",(pid,)).fetchone()[0]
        def take(_):
            with psycopg.connect(database_url,connect_timeout=3) as writer:
                saldo=writer.execute('SELECT saldo FROM lotes WHERE id=%s FOR UPDATE',(lid,)).fetchone()[0]
                if saldo<7:
                    return False
                writer.execute('UPDATE lotes SET saldo=saldo-7 WHERE id=%s',(lid,))
                writer.execute('INSERT INTO movimentos(lote_id,quantidade) VALUES (%s,7)',(lid,))
                return True
        with ThreadPoolExecutor(max_workers=5) as pool:
            accepted=sum(pool.map(take,range(5)))
        with psycopg.connect(database_url) as check:
            saldo=check.execute('SELECT saldo FROM lotes WHERE id=%s',(lid,)).fetchone()[0]
            moves=check.execute('SELECT count(*) FROM movimentos').fetchone()[0]
        assert accepted==1 and saldo==3 and moves==1
        print(json.dumps({'postgres_local':True,'workers':5,'accepted':accepted,'balance':str(saldo),'movements':moves,'application_migrated':False}))
    finally:
        if started:
            subprocess.run(['docker','stop','--time','10',name],check=True,capture_output=True,timeout=30)


if __name__=='__main__':
    main()
