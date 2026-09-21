import secrets
import unittest
from unittest.mock import patch

import app as web
from admin_cli import manage
from werkzeug.security import check_password_hash
import test_app as fixtures


class FirstAccessTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.UniVetAppTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
        self.client = self.fixture.client
        self.temporary = secrets.token_urlsafe(24)
        manage(self.fixture.db_path, 'create-user', 'fictitious.individual', password=self.temporary)
        self.client.post('/login',data={'login':'fictitious.individual','senha':self.temporary})

    def test_forced_page_only_and_invalid_changes_stay_restricted(self):
        for path in ('/pagina-inicial','/tutores','/consultas','/estoque'):
            self.assertTrue(self.client.get(path).location.endswith('/conta/senha'))
        self.assertEqual(self.client.get('/api/estoque/resumo').status_code,403)
        html = self.client.get('/conta/senha').get_data(as_text=True)
        self.assertIn('Defina sua nova senha',html)
        self.assertNotIn('id="main-sidebar"',html)
        for new, confirmation in [('short','short'),(self.temporary,self.temporary),('frase longa com espaços','divergente')]:
            self.client.post('/conta/senha', data={'senha_atual':self.temporary,'nova_senha':new,'confirmacao':confirmation})
            self.assertEqual(self.client.get('/api/estoque/resumo').status_code,403)

    def test_temporary_invalidated_previous_sessions_revoked_and_hash_only(self):
        from support import FormClient
        second = FormClient(web.app, web.app.response_class)
        second.post('/login',data={'login':'fictitious.individual','senha':self.temporary})
        final = 'frase fictícia longa ' + secrets.token_urlsafe(12)
        response = self.client.post('/conta/senha', data={'senha_atual':self.temporary,'nova_senha':final,'confirmacao':final})
        self.assertTrue(response.location.endswith('/pagina-inicial'))
        self.assertEqual(self.client.get('/api/estoque/resumo').status_code,200)
        self.assertEqual(second.get('/api/estoque/resumo').status_code,401)
        with self.fixture._conexao() as conn:
            row = conn.execute("SELECT senha_hash,must_change_password FROM usuarios WHERE login='fictitious.individual'").fetchone()
            self.assertFalse(row[1])
            self.assertNotIn(final,row[0])
            self.assertNotIn(self.temporary,row[0])
            self.assertTrue(check_password_hash(row[0],final))
            self.assertFalse(check_password_hash(row[0],self.temporary))
        self.client.post('/logout')
        self.client.post('/login',data={'login':'fictitious.individual','senha':self.temporary})
        self.assertEqual(self.client.get('/api/estoque/resumo').status_code,401)

    def test_concurrent_admin_reset_cannot_be_overwritten(self):
        original_hash = web.password_hash
        reset = secrets.token_urlsafe(24)
        def reset_during_hash(value):
            result = original_hash(value)
            manage(self.fixture.db_path,'reset-password','fictitious.individual',password=reset)
            return result
        final = secrets.token_urlsafe(24)
        with patch.object(web,'password_hash',side_effect=reset_during_hash):
            self.client.post('/conta/senha',data={'senha_atual':self.temporary,'nova_senha':final,'confirmacao':final})
        with self.fixture._conexao() as conn:
            row=conn.execute("SELECT senha_hash,must_change_password FROM usuarios WHERE login='fictitious.individual'").fetchone()
            self.assertTrue(check_password_hash(row[0],reset))
            self.assertTrue(row[1])
        self.assertEqual(self.client.get('/api/estoque/resumo').status_code,401)
