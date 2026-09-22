"""PostgreSQL efêmero criado por nós; nunca aceita URL externa nem monta dados."""
import os
import secrets
import subprocess
import time
import uuid
import psycopg
from psycopg import sql
from database import close_pools


class LocalPostgres:
    def __init__(self):
        self.name='univet-test-'+uuid.uuid4().hex[:12]
        self.password=secrets.token_hex(24)
        self.started=False

    def start(self):
        subprocess.run(['docker','run','--detach','--rm','--name',self.name,
            '-e','POSTGRES_PASSWORD','-p','127.0.0.1::5432','postgres:16-alpine'],
            env=dict(os.environ,POSTGRES_PASSWORD=self.password),check=True,capture_output=True,timeout=120)
        self.started=True
        address=subprocess.check_output(['docker','port',self.name,'5432/tcp'],text=True,timeout=10).strip()
        host,self.port=address.rsplit(':',1)
        if host!='127.0.0.1':
            raise RuntimeError('Isolamento de rede inválido.')
        last_error = None
        for _ in range(240):
            try:
                with psycopg.connect(self.url('postgres'),connect_timeout=1):
                    return self
            except psycopg.OperationalError as error:
                last_error = error
                time.sleep(.25)
        self.stop()
        raise RuntimeError(f'PostgreSQL descartável não iniciou: {last_error}')

    def url(self,name):
        return f'postgresql://postgres:{self.password}@127.0.0.1:{self.port}/{name}'

    def database(self):
        name='univet_test_'+uuid.uuid4().hex
        with psycopg.connect(self.url('postgres'),autocommit=True) as conn:
            conn.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(name)))
        return self.url(name)

    def stop(self):
        close_pools()
        if self.started:
            try:
                subprocess.run(['docker','stop','--time','5',self.name],check=True,capture_output=True,timeout=15)
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
                subprocess.run(['docker','rm','--force',self.name],check=False,capture_output=True,timeout=15)
            self.started=False

    def __enter__(self):
        try:
            return self.start()
        except Exception:
            self.stop()
            raise

    def __exit__(self,*args):
        self.stop()
