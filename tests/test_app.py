import sqlite3
import tempfile
import unittest
from pathlib import Path

import app as app_module
import init_db as init_db_module


class UniVetAppTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "banco_teste.db"
        self.database_original_app = app_module.DATABASE
        self.database_original_init = init_db_module.DATABASE
        app_module.DATABASE = self.db_path
        init_db_module.DATABASE = self.db_path
        init_db_module.init_db()
        app_module.limpar_caches_referencia()
        app_module.app.config.update(TESTING=True)
        self.client = app_module.app.test_client()
        self._garantir_dados_base()

    def tearDown(self):
        app_module.DATABASE = self.database_original_app
        init_db_module.DATABASE = self.database_original_init
        app_module.limpar_caches_referencia()
        self.temp_dir.cleanup()

    def _conexao(self):
        conexao = sqlite3.connect(self.db_path)
        conexao.row_factory = sqlite3.Row
        return conexao

    def _garantir_dados_base(self):
        conexao = self._conexao()
        tutor = conexao.execute("SELECT id FROM tutores LIMIT 1").fetchone()
        if not tutor:
            conexao.execute(
                "INSERT INTO tutores (nome, telefone, cpf, endereco) VALUES (?, ?, ?, ?)",
                ("Tutor Teste", "(11) 99999-0000", "529.982.247-25", "Rua das Flores, 100"),
            )
            tutor_id = conexao.execute("SELECT last_insert_rowid()").fetchone()[0]
        else:
            tutor_id = tutor["id"]

        especie = conexao.execute("SELECT id, nome FROM especies ORDER BY id ASC LIMIT 1").fetchone()
        raca = conexao.execute("SELECT id, nome FROM racas WHERE especie_id = ? ORDER BY id ASC LIMIT 1", (especie["id"],)).fetchone()
        pet = conexao.execute("SELECT id FROM pets LIMIT 1").fetchone()
        if not pet:
            conexao.execute(
                """
                INSERT INTO pets (nome, especie, raca, tutor_id, historico, idade, especie_id, raca_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                ("Pet Teste", especie["nome"], raca["nome"], tutor_id, "Paciente alérgico.", "3 anos", especie["id"], raca["id"]),
            )
        conexao.commit()
        conexao.close()

    def _login(self, usuario, senha):
        return self.client.post(
            "/login",
            data={"login": usuario, "senha": senha},
            follow_redirects=True,
        )

    def _id_pet(self):
        conexao = self._conexao()
        pet_id = conexao.execute("SELECT id FROM pets ORDER BY id ASC LIMIT 1").fetchone()["id"]
        conexao.close()
        return pet_id

    def _id_servico(self):
        conexao = self._conexao()
        servico_id = conexao.execute("SELECT id FROM servicos ORDER BY id ASC LIMIT 1").fetchone()["id"]
        conexao.close()
        return servico_id

    def _id_veterinario(self, nome):
        conexao = self._conexao()
        registro = conexao.execute("SELECT id FROM veterinarios WHERE nome = ?", (nome,)).fetchone()
        conexao.close()
        return registro["id"] if registro else None

    def _criar_consulta(self, data_hora, veterinario_id, diagnostico="", tratamento="", vacinas="", observacoes=""):
        conexao = self._conexao()
        servico_id = conexao.execute("SELECT id, nome, duracao_minutos FROM servicos ORDER BY id ASC LIMIT 1").fetchone()
        conexao.execute(
            """
            INSERT INTO consultas (
                data_hora, data_fim, pet_id, servico_id, tipo_consulta, duracao_total_minutos,
                veterinario_id, tipo_atendimento, observacoes, diagnostico, tratamento, vacinas,
                status, confirmacao_status
            ) VALUES (?, replace(substr(datetime(?, '+' || ? || ' minutes'), 1, 16), ' ', 'T'), ?, ?, ?, ?, ?, 'Presencial', ?, ?, ?, ?, 'Agendada', 'Confirmada')
            """,
            (
                data_hora,
                data_hora,
                servico_id["duracao_minutos"],
                self._id_pet(),
                servico_id["id"],
                servico_id["nome"],
                servico_id["duracao_minutos"],
                veterinario_id,
                observacoes,
                diagnostico,
                tratamento,
                vacinas,
            ),
        )
        consulta_id = conexao.execute("SELECT last_insert_rowid()").fetchone()[0]
        conexao.commit()
        conexao.close()
        return consulta_id

    def test_logins_padrao_funcionam(self):
        resposta_admin = self._login("admin", "123456")
        self.assertIn("Página inicial", resposta_admin.get_data(as_text=True))

        self.client.get("/logout", follow_redirects=True)

        resposta_fernanda = self._login("fernanda.calixto", "Fer123")
        self.assertIn("Página inicial", resposta_fernanda.get_data(as_text=True))
        self.assertIn("Dra. Fernanda Calixto", resposta_fernanda.get_data(as_text=True))

    def test_apenas_usuarios_autorizados_permanecem_no_banco(self):
        conexao = self._conexao()
        usuarios = conexao.execute("SELECT login, perfil, ativo FROM usuarios ORDER BY login ASC").fetchall()
        conexao.close()
        self.assertEqual(
            [(item["login"], item["perfil"], item["ativo"]) for item in usuarios],
            [("admin", "admin", 1), ("fernanda.calixto", "veterinaria", 1)],
        )

    def test_exclusao_de_veterinario_redistribui_consultas(self):
        self._login("admin", "123456")
        alvo_id = self._id_veterinario("Dr. Rafael Moreira")
        self.assertIsNotNone(alvo_id)
        consulta_id = self._criar_consulta(
            "2026-04-08T09:00",
            alvo_id,
            observacoes="Consulta vinculada ao veterinário a ser excluído.",
        )

        resposta = self.client.post(
            f"/veterinarios/{alvo_id}/excluir",
            data={"confirmar_exclusao": "sim"},
            follow_redirects=True,
        )
        texto = resposta.get_data(as_text=True)
        self.assertIn("foram transferidas", texto)

        conexao = self._conexao()
        veterinario = conexao.execute("SELECT id FROM veterinarios WHERE id = ?", (alvo_id,)).fetchone()
        consulta = conexao.execute("SELECT veterinario_id FROM consultas WHERE id = ?", (consulta_id,)).fetchone()
        conexao.close()
        self.assertIsNone(veterinario)
        self.assertNotEqual(consulta["veterinario_id"], alvo_id)

    def test_exclusao_de_veterinario_exige_confirmacao(self):
        self._login("admin", "123456")
        alvo_id = self._id_veterinario("Dr. Rafael Moreira")
        resposta = self.client.post(f"/veterinarios/{alvo_id}/excluir", data={}, follow_redirects=True)
        self.assertIn("Confirme a exclusão para continuar.", resposta.get_data(as_text=True))

    def test_historico_clinico_da_consulta_exibe_prontuario_do_paciente(self):
        self._login("fernanda.calixto", "Fer123")
        veterinario_id = self._id_veterinario("Dra. Fernanda Calixto")
        self._criar_consulta(
            "2026-04-05T10:00",
            veterinario_id,
            diagnostico="Otite externa leve.",
            tratamento="Limpeza auricular e anti-inflamatório.",
            vacinas="Vacina V10 em dia.",
            observacoes="Paciente tranquilo.",
        )
        consulta_id = self._criar_consulta(
            "2026-04-06T11:00",
            veterinario_id,
            diagnostico="Retorno sem sinais de inflamação.",
            tratamento="Manter limpeza por mais 5 dias.",
            vacinas="Sem nova aplicação.",
            observacoes="Boa resposta ao tratamento.",
        )

        resposta = self.client.get(f"/historico/consultas/{consulta_id}", follow_redirects=True)
        texto = resposta.get_data(as_text=True)
        self.assertIn("Linha do tempo do paciente", texto)
        self.assertIn("Otite externa leve.", texto)
        self.assertIn("Retorno sem sinais de inflamação.", texto)
        self.assertIn("Boa resposta ao tratamento.", texto)


if __name__ == "__main__":
    unittest.main()
