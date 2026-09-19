import os
import secrets
import sqlite3
import subprocess
import sys
import unittest
from unittest.mock import patch

import app as web
import init_db
from admin_cli import manage
from security import password_hash
import test_app as fixtures


class SecurityTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.UniVetAppTests()
        self.fixture.setUp()
        self.client = self.fixture.client

    def tearDown(self):
        self.fixture.tearDown()

    def login(self, role='admin'):
        account = next(u for u in init_db.USUARIOS_PADRAO if u[2] == role)
        self.assertEqual(self.client.post('/login', data={'login':account[0], 'senha':account[3]}).status_code, 302)

    def test_csrf_required_and_valid_form_works(self):
        raw = web.app.test_client()
        self.assertEqual(raw.post('/login', data={'login':'admin', 'senha':'invalid'}).status_code, 400)
        self.login()
        self.assertEqual(self.client.post('/estoque/categorias', data={'nome':'CSRF denied','csrf_token':'invalid'}).status_code, 400)
        self.assertEqual(self.client.post('/estoque/categorias', data={'nome':'CSRF accepted'}).status_code, 302)
        with self.fixture._conexao() as conn:
            self.assertEqual(conn.execute("SELECT count(*) FROM categorias WHERE nome='CSRF denied'").fetchone()[0], 0)

    def test_session_revocation_and_logout_replay(self):
        self.login()
        cookie = self.client.get_cookie('session').value
        self.assertEqual(self.client.post('/logout').status_code, 302)
        self.client.set_cookie('session', cookie)
        self.assertEqual(self.client.get('/api/estoque/resumo').status_code, 401)
        self.login()
        with self.fixture._conexao() as conn:
            conn.execute("UPDATE usuarios SET ativo=0 WHERE login='admin'")
        self.assertEqual(self.client.get('/api/estoque/resumo').status_code, 401)

    def test_session_rotation_expiry_and_forged_legacy(self):
        with self.client.session_transaction() as state:
            state['sid']='attacker-chosen'
        self.login()
        with self.client.session_transaction() as state:
            self.assertNotEqual(state['sid'], 'attacker-chosen')
        with self.fixture._conexao() as conn:
            conn.execute('UPDATE auth_sessions SET last_seen=0')
        self.assertEqual(self.client.get('/api/estoque/resumo').status_code, 401)
        with self.client.session_transaction() as state:
            state.clear(); state.update(usuario_id=1, usuario_perfil='admin')
        self.assertEqual(self.client.get('/api/estoque/resumo').status_code, 401)

    def test_permissions_ids_and_mass_assignment(self):
        self.login('veterinaria')
        with self.client.session_transaction() as state:
            state['usuario_perfil']='admin'  # Perfil antigo do cookie não concede privilégio.
        for identifier in (1,2,999999):
            self.assertEqual(self.client.post(f'/estoque/produtos/{identifier}/alternar', data={'role':'admin','usuario_id':1}).status_code,403)
        self.assertEqual(self.client.get('/estoque/exportar/posicao.csv').status_code,403)
        self.assertEqual(self.client.get('/api/estoque/produtos').status_code,200)
        with self.client.session_transaction() as state:
            self.assertEqual(state['usuario_perfil'],'veterinaria')
        self.client.post('/pets/1/condicoes',data={'condicao':'Condição fictícia','status':'Ativa','usuario_id':'1','role':'admin'})
        with self.fixture._conexao() as conn:
            record=conn.execute("SELECT usuario_nome FROM condicoes_clinicas WHERE condicao='Condição fictícia'").fetchone()
            self.assertEqual(record[0],'Veterinária Demo')

    def test_html_sql_csv_and_inputs(self):
        self.client.post('/login',data={'login':"' OR 1=1 --",'senha':'invalid'})
        self.assertEqual(self.client.get('/api/estoque/resumo').status_code,401)
        self.login()
        payload='<script>alert(1)</script>'
        self.client.post('/estoque/categorias',data={'nome':payload})
        text=self.client.get('/estoque/categorias').get_data(as_text=True)
        self.assertNotIn(payload,text); self.assertIn('&lt;script&gt;',text)
        self.assertEqual(self.client.get('/api/estoque/produtos',query_string={'busca':"' OR 1=1 --"}).status_code,200)
        for value in ('nan','inf','-1','1e100'):
            self.assertEqual(self.client.post('/estoque/produtos/novo',data={'nome':'invalid','tipo':'Produto','estoque_minimo':value}).status_code,400)
        response=web.csv_response('test.csv',['text'],[['=1+1'],['  @SUM(1)'],[-2]])
        self.assertIn("'=1+1",response.get_data(as_text=True))
        self.assertIn("'  @SUM",response.get_data(as_text=True))
        self.assertEqual(self.client.post('/estoque/categorias',data={'nome':'x'*513}).status_code,400)

    def test_headers_and_cookie(self):
        self.login()
        response=self.client.get('/pagina-inicial')
        self.assertEqual(response.headers['Cache-Control'],'no-store')
        self.assertEqual(response.headers['X-Frame-Options'],'DENY')
        self.assertIn("frame-ancestors 'none'",response.headers['Content-Security-Policy'])
        self.assertIn("script-src 'self' 'nonce-",response.headers['Content-Security-Policy'])
        self.assertNotIn('onclick=',response.get_data(as_text=True))
        cookie=self.client.get_cookie('session')
        self.assertTrue(cookie.http_only); self.assertEqual(cookie.same_site,'Lax')

    def test_rate_limit_login_and_api(self):
        for _ in range(10):
            self.client.post('/login',data={'login':'nonexistent','senha':'invalid'})
        self.assertEqual(self.client.post('/login',data={'login':'nonexistent','senha':'invalid'}).status_code,429)
        self.login()
        with self.fixture._conexao() as conn:
            conn.execute('DELETE FROM rate_limits')
        # One real request creates the shared counter; advance it without a load attack.
        self.client.get('/api/estoque/resumo')
        with self.fixture._conexao() as conn:
            conn.execute('UPDATE rate_limits SET hits=180')
        self.assertEqual(self.client.get('/api/estoque/resumo').status_code,429)

    def test_admin_reset_and_change_password(self):
        self.login()
        new=secrets.token_urlsafe(24)
        manage(self.fixture.db_path,'reset-password','admin',password=new)
        self.assertEqual(self.client.get('/api/estoque/resumo').status_code,401)
        self.client.post('/login',data={'login':'admin','senha':new})
        self.assertEqual(self.client.get('/api/estoque/resumo').status_code,403)
        newer=secrets.token_urlsafe(24)
        response=self.client.post('/conta/senha',data={'senha_atual':new,'nova_senha':newer,'confirmacao':newer})
        self.assertEqual(response.status_code,302)
        self.assertEqual(self.client.get('/api/estoque/resumo').status_code,401)
        self.client.post('/login',data={'login':'admin','senha':newer})
        self.assertEqual(self.client.get('/api/estoque/resumo').status_code,200)
        with self.assertRaises(ValueError):
            manage(self.fixture.db_path,'deactivate','admin')

    def test_migration_preserves_accounts_no_demo_by_default(self):
        password=secrets.token_urlsafe(24)
        manage(self.fixture.db_path,'create-user','individual',password=password)
        with self.fixture._conexao() as conn:
            before=conn.execute("SELECT senha_hash FROM usuarios WHERE login='individual'").fetchone()[0]
        init_db.init_db()
        with self.fixture._conexao() as conn:
            self.assertEqual(conn.execute("SELECT senha_hash FROM usuarios WHERE login='individual'").fetchone()[0],before)
        with self.assertRaises(ValueError):
            manage(self.fixture.db_path,'bootstrap','another',password=password)

    def test_production_rejects_missing_secret(self):
        env=dict(os.environ,UNIVET_ENV='production')
        env.pop('SECRET_KEY',None)
        result=subprocess.run([sys.executable,'-c','import app'],env=env,capture_output=True,timeout=10)
        self.assertNotEqual(result.returncode,0)

    def test_production_https_headers_and_secure_config(self):
        import json
        env=dict(os.environ,UNIVET_ENV='production',SECRET_KEY=secrets.token_hex(32))
        env.pop('UNIVET_TRUST_PROXY',None)
        script="""import app,json
c=app.app.test_client()
r=c.get('/static/style.css',base_url='https://localhost')
print(json.dumps([app.app.config['SESSION_COOKIE_SECURE'],app.app.debug,r.headers.get('Strict-Transport-Security'),c.get('/static/style.css',base_url='http://localhost').status_code]))
"""
        result=subprocess.run([sys.executable,'-c',script],env=env,capture_output=True,text=True,timeout=10,check=True)
        self.assertEqual(json.loads(result.stdout),[True,False,'max-age=31536000',400])


if __name__ == '__main__':
    unittest.main()
