from concurrent.futures import ThreadPoolExecutor
import threading
import unittest
from unittest.mock import patch
from werkzeug.datastructures import MultiDict

import app as web
import test_app as fixtures


class AgendaConcurrencyTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fixtures.UniVetAppTests()
        self.fixture.setUp()
        with self.fixture._conexao() as conn:
            self.pet=conn.execute('SELECT id FROM pets LIMIT 1').fetchone()[0]
            self.service=conn.execute('SELECT id FROM servicos WHERE duracao_minutos=20 LIMIT 1').fetchone()[0]
            self.vet=conn.execute('SELECT id FROM veterinarios LIMIT 1').fetchone()[0]

    def tearDown(self):
        self.fixture.tearDown()

    def data(self, hour):
        return MultiDict({'data_hora':f'2099-01-05T{hour}','pet_id':str(self.pet),'servico_id':str(self.service),'veterinario_id':str(self.vet),'tipo_atendimento':'Presencial','confirmacao_status':'Pendente','status':'Agendada'})

    def test_overlapping_requests_only_one_and_correct_history(self):
        barrier=threading.Barrier(2)
        def create(hour):
            with web.app.test_request_context():
                barrier.wait(timeout=10)
                return web.salvar_consulta(self.data(hour))[0]
        with ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(create,['09:00','09:10']))
        self.assertEqual(sum(results),1)
        with self.fixture._conexao() as conn:
            records=conn.execute("SELECT id FROM consultas WHERE data_hora LIKE '2099-01-05%'").fetchall()
            self.assertEqual(len(records),1)
            self.assertEqual(conn.execute("SELECT count(*) FROM historico_alteracoes WHERE entidade='consultas' AND registro_id=?",(records[0][0],)).fetchone()[0],1)

    def test_history_failure_rolls_back_consultation(self):
        with web.app.test_request_context(), patch.object(web,'registrar_historico',side_effect=RuntimeError('injected test failure')):
            with self.assertRaises(RuntimeError):
                web.salvar_consulta(self.data('10:00'))
        with self.fixture._conexao() as conn:
            self.assertEqual(conn.execute("SELECT count(*) FROM consultas WHERE data_hora LIKE '2099-01-05%'").fetchone()[0],0)
