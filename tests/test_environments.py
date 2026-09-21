"""Somente bancos fictícios temporários. Nenhuma conta real é criada."""
import json
import os
from pathlib import Path
import secrets
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from flask import Flask
from itsdangerous import BadSignature
from config import load_settings, verify_database_environment
from security import EnvironmentSessionInterface


class EnvironmentTests(unittest.TestCase):
    def test_no_cross_environment_fallback(self):
        for mode, wrong in [('demo', 'DATABASE_URL'), ('production', 'DEMO_DATABASE_URL')]:
            with self.subTest(mode=mode), self.assertRaises(RuntimeError):
                load_settings({'UNIVET_ENV':mode, wrong:'sqlite:////tmp/not-opened.db'})
        with self.assertRaises(RuntimeError):
            load_settings({'UNIVET_ENV':'invalid'})

    def test_same_database_aliases_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'one.db'
            path.touch()
            alias = Path(directory)/'two.db'
            alias.symlink_to(path)
            with self.assertRaises(RuntimeError):
                load_settings({'UNIVET_ENV':'demo', 'DATABASE_URL':'sqlite:///'+str(path), 'DEMO_DATABASE_URL':'sqlite:///'+str(alias)})

    def test_sqlite_production_rejects_ephemeral_or_implicit_storage(self):
        env = {'UNIVET_ENV':'production','DATABASE_URL':'sqlite:////tmp/not-opened.db'}
        with self.assertRaises(RuntimeError):
            load_settings(env)
        with self.assertRaises(RuntimeError):
            load_settings(dict(env, UNIVET_SQLITE_PERSISTENT='1', RENDER='true'))
        self.assertEqual(load_settings(dict(env, UNIVET_SQLITE_PERSISTENT='1')).environment, 'production')
        with self.assertRaises(RuntimeError):
            load_settings(dict(env, DATABASE_URL='postgresql://secret:secret@invalid/db'))

    def test_database_identity_cannot_be_relabelled(self):
        with sqlite3.connect(':memory:') as conn:
            verify_database_environment(conn, 'demo', initialize=True)
            for mode in ('production','development','test'):
                with self.assertRaises(RuntimeError):
                    verify_database_environment(conn, mode, initialize=True)
        with sqlite3.connect(':memory:') as conn:
            conn.execute('CREATE TABLE old_data(id INTEGER)')
            with self.assertRaises(RuntimeError):
                verify_database_environment(conn, 'production', initialize=True)
            self.assertIsNone(conn.execute("SELECT 1 FROM sqlite_master WHERE name='univet_environment'").fetchone())

    def test_demo_session_rejected_even_with_same_secret(self):
        apps = [Flask('demo'),Flask('production')]
        key = secrets.token_hex(32)
        for app, mode in zip(apps, ('demo','production')):
            app.config.update(SECRET_KEY=key, UNIVET_ENV=mode)
        serializers = [EnvironmentSessionInterface().get_signing_serializer(app) for app in apps]
        token = serializers[0].dumps({'usuario_id':1,'sid':'fictitious'})
        with self.assertRaises(BadSignature):
            serializers[1].loads(token)

    def run_isolated(self, mode, script):
        with tempfile.TemporaryDirectory(prefix='univet-mode-') as directory:
            env = {k:v for k,v in os.environ.items() if k not in ('DATABASE_URL','DEMO_DATABASE_URL','UNIVET_DATABASE','RENDER','UNIVET_TRUST_PROXY')}
            env.update(UNIVET_ENV=mode, SECRET_KEY=secrets.token_hex(32), UNIVET_SQLITE_PERSISTENT='1')
            env['DATABASE_URL' if mode=='production' else 'DEMO_DATABASE_URL'] = 'sqlite:///'+str(Path(directory)/'isolated.db')
            result = subprocess.run([sys.executable, '-c', script], env=env, capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)
            return json.loads(result.stdout.splitlines()[-1])

    def test_production_clean_migrate_twice_demo_absent_and_rejected(self):
        result = self.run_isolated('production', '''
import init_db, sqlite3, json
init_db.init_db()
init_db.init_db()
try:
    init_db.init_db(seed_demo=True)
except RuntimeError:
    rejected=True
else:
    rejected=False
import app
from support import FormClient
c=FormClient(app.app,app.app.response_class)
c.get('/login',base_url='https://localhost')
with c.session_transaction() as state:
    token=state['csrf_token']
r=c.post('/login',base_url='https://localhost',data={'login':'admin','senha':'123456','csrf_token':token})
conn=sqlite3.connect(init_db.DATABASE)
counts=[conn.execute('SELECT count(*) FROM '+t).fetchone()[0] for t in ('usuarios','tutores','pets','consultas','produtos','fornecedores')]
print(json.dumps([rejected,counts,r.status_code,c.get('/api/estoque/resumo',base_url='https://localhost').status_code]))
''')
        self.assertEqual(result, [True,[0,0,0,0,0,0],200,401])

    def test_demo_seed_navigation_and_environment_badge(self):
        result = self.run_isolated('demo', '''
import init_db, json
init_db.init_db(seed_demo=True)
import app
from support import FormClient
c=FormClient(app.app,app.app.response_class)
c.post('/login',data={'login':'admin','senha':'123456'})
print(json.dumps([c.get(p).status_code for p in ('/pagina-inicial','/consultas','/estoque','/api/estoque/resumo')]+['Ambiente de demonstração' in c.get('/pagina-inicial').get_data(as_text=True)]))
''')
        self.assertEqual(result,[200,200,200,200,True])

    def test_admin_cli_refuses_password_output_to_pipe(self):
        result = subprocess.run([sys.executable,'admin_cli.py','--database','not-opened.db','create-user','--login','fictitious'],capture_output=True,text=True,timeout=10)
        self.assertNotEqual(result.returncode,0)
        self.assertEqual(result.stdout,'')
        self.assertIn('terminal local interativo',result.stderr)
