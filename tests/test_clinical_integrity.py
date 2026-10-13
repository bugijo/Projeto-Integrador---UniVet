import unittest
from unittest.mock import patch

import app as web
import test_app as fixtures


class ClinicalIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.UniVetAppTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
        self.client = self.fixture.client
        self.client.post('/login',data={'login':'admin','senha':'123456'})

    def test_history_failure_rolls_back_patient_and_tutor_updates(self):
        with self.fixture._conexao() as conn:
            tutor = dict(conn.execute('SELECT * FROM tutores LIMIT 1').fetchone())
            pet = dict(conn.execute('SELECT * FROM pets LIMIT 1').fetchone())
        for table, row, endpoint in [('tutores',tutor,'tutores'),('pets',pet,'pets')]:
            data=dict(row, nome='Não deve persistir')
            data={k:v for k,v in data.items() if v is not None}
            with patch.object(web,'registrar_historico',side_effect=RuntimeError('injected')):
                with self.assertRaises(RuntimeError):
                    self.client.post(f'/{endpoint}/{row["id"]}/editar',data=data)
            with self.fixture._conexao() as conn:
                self.assertEqual(dict(conn.execute(f'SELECT * FROM {table} WHERE id=?',(row['id'],)).fetchone()),row)

    def test_cancel_preserves_record_and_is_idempotent(self):
        with self.fixture._conexao() as conn:
            record=conn.execute("SELECT * FROM consultas WHERE status='Agendada' LIMIT 1").fetchone()
            identifier=record['id']
        for _ in range(2):
            self.assertEqual(self.client.post(f'/consultas/{identifier}/excluir').status_code,302)
        with self.fixture._conexao() as conn:
            updated=conn.execute('SELECT * FROM consultas WHERE id=?',(identifier,)).fetchone()
            self.assertEqual(updated['status'],'Cancelada')
            self.assertEqual(updated['observacoes'],record['observacoes'])
            self.assertEqual(conn.execute("SELECT count(*) FROM historico_alteracoes WHERE entidade='consultas' AND registro_id=? AND acao='cancelado'",(identifier,)).fetchone()[0],1)

    def test_completed_consultation_and_author_not_deleted(self):
        with self.fixture._conexao() as conn:
            record=conn.execute('SELECT id,veterinario_id FROM consultas LIMIT 1').fetchone()
            conn.execute("UPDATE consultas SET status='Concluida' WHERE id=?",(record[0],))
        self.client.post(f'/consultas/{record[0]}/excluir')
        self.client.post(f'/veterinarios/{record[1]}/excluir',data={'confirmar_exclusao':'sim'})
        with self.fixture._conexao() as conn:
            row=conn.execute('SELECT status,veterinario_id FROM consultas WHERE id=?',(record[0],)).fetchone()
            self.assertEqual(tuple(row),('Concluida',record[1]))
            self.assertIsNotNone(conn.execute('SELECT id FROM veterinarios WHERE id=?',(record[1],)).fetchone())

    def test_conditions_block_patient_deletion_even_without_consultation(self):
        with self.fixture._conexao() as conn:
            pet=conn.execute('SELECT id FROM pets WHERE id NOT IN (SELECT pet_id FROM consultas) LIMIT 1').fetchone()[0]
            conn.execute("UPDATE pets SET historico='' WHERE id=?",(pet,))
        self.client.post(f'/pets/{pet}/condicoes',data={'condicao':'Condição fictícia','status':'Ativa'})
        self.client.post(f'/pets/{pet}/excluir')
        with self.fixture._conexao() as conn:
            self.assertIsNotNone(conn.execute('SELECT id FROM pets WHERE id=?',(pet,)).fetchone())
            self.assertEqual(conn.execute('SELECT count(*) FROM condicoes_clinicas WHERE pet_id=?',(pet,)).fetchone()[0],1)
