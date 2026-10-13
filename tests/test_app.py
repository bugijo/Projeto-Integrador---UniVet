import sqlite3
import tempfile
import unittest
from pathlib import Path

import app as app_module
import init_db as init_db_module
from support import FormClient


class UniVetAppTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "banco_teste.db"
        self.database_original_app = app_module.DATABASE
        self.database_original_init = init_db_module.DATABASE
        app_module.DATABASE = self.db_path
        init_db_module.DATABASE = self.db_path
        init_db_module.init_db(seed_demo=True)
        app_module.limpar_caches_referencia()
        app_module.app.config.update(TESTING=True)
        self.client = FormClient(app_module.app, app_module.app.response_class)
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

        self.client.post("/logout", follow_redirects=True)

        resposta_fernanda = self._login("vet.demo", "Fer123")
        self.assertIn("Página inicial", resposta_fernanda.get_data(as_text=True))
        self.assertIn("Veterinária Demo", resposta_fernanda.get_data(as_text=True))

    def test_exportacoes_csv_exigem_login_e_retornam_csv(self):
        self.assertEqual(self.client.get("/estoque/exportar/posicao.csv").status_code, 302)
        self._login("admin", "123456")
        for rota in ("/estoque/exportar/posicao.csv", "/estoque/exportar/movimentacoes.csv", "/estoque/exportar/consumo.csv"):
            resposta = self.client.get(rota)
            self.assertEqual(resposta.status_code, 200)
            self.assertIn("text/csv", resposta.content_type)
            self.assertTrue(resposta.get_data().startswith(b"\xef\xbb\xbf"))

    def test_filtros_invalidos_de_paginacao_nao_geram_erro_500(self):
        self._login("admin", "123456")
        for rota in ("/estoque/produtos?pagina=abc", "/estoque/lotes?pagina=-10", "/estoque/movimentacoes?por_pagina=texto", "/estoque/fornecedores?pagina=abc"):
            resposta = self.client.get(rota)
            self.assertNotEqual(resposta.status_code, 500)

    def test_telas_de_analise_do_estoque_renderizam(self):
        self._login("admin", "123456")
        for rota in ("/estoque", "/estoque/relatorios", "/estoque/relatorios?dias=30&categoria_id=999999", "/estoque/fornecedores?status=ativo"):
            resposta = self.client.get(rota)
            self.assertEqual(resposta.status_code, 200, rota)
            self.assertNotIn("Traceback", resposta.get_data(as_text=True))

    def test_api_minima_de_estoque_retorna_dados_paginados(self):
        self.assertEqual(self.client.get("/api/estoque/resumo").status_code, 401)
        self._login("admin", "123456")
        resposta = self.client.get("/api/estoque/produtos?pagina=1&por_pagina=5")
        self.assertEqual(resposta.status_code, 200)
        self.assertIn("meta", resposta.get_json())
        self.assertIn("data", resposta.get_json())
        self.assertEqual(self.client.get("/api/estoque/resumo").status_code, 200)
        self.assertEqual(self.client.get("/api/estoque/movimentacoes?por_pagina=5").status_code, 200)

    def test_apenas_usuarios_autorizados_permanecem_no_banco(self):
        conexao = self._conexao()
        usuarios = conexao.execute("SELECT login, perfil, ativo FROM usuarios ORDER BY login ASC").fetchall()
        conexao.close()
        self.assertEqual(
            [(item["login"], item["perfil"], item["ativo"]) for item in usuarios],
            [("admin", "admin", 1), ("vet.demo", "veterinaria", 1)],
        )

    def test_exclusao_de_veterinario_redistribui_consultas(self):
        self._login("admin", "123456")
        alvo_id = self._id_veterinario("Veterinário Demo")
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
        alvo_id = self._id_veterinario("Veterinário Demo")
        resposta = self.client.post(f"/veterinarios/{alvo_id}/excluir", data={}, follow_redirects=True)
        self.assertIn("Confirme a exclusão para continuar.", resposta.get_data(as_text=True))

    def test_historico_clinico_da_consulta_exibe_prontuario_do_paciente(self):
        self._login("vet.demo", "Fer123")
        veterinario_id = self._id_veterinario("Veterinária Demo")
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

    def test_prontuario_pet_adiciona_condicao_e_inicia_atendimento_com_paciente(self):
        self._login("vet.demo", "Fer123")
        pet_id = self._id_pet()

        resposta = self.client.get(f"/pets/{pet_id}/historico-clinico")
        texto = resposta.get_data(as_text=True)
        self.assertEqual(resposta.status_code, 200)
        self.assertIn("Condições e observações permanentes", texto)
        self.assertIn("Novo atendimento", texto)

        resposta = self.client.post(
            f"/pets/{pet_id}/condicoes",
            data={
                "condicao": "Dermatite alérgica",
                "status": "Ativa",
                "observacoes": "Acompanhar resposta ao tratamento.",
            },
            follow_redirects=True,
        )
        texto = resposta.get_data(as_text=True)
        self.assertEqual(resposta.status_code, 200)
        self.assertIn("Dermatite alérgica", texto)
        self.assertIn("Condição clínica adicionada ao prontuário.", texto)

        resposta = self.client.get(f"/consultas/nova?pet_id={pet_id}")
        texto = resposta.get_data(as_text=True)
        self.assertEqual(resposta.status_code, 200)
        self.assertIn(f'<option value="{pet_id}" selected>', texto)

    def test_api_disponibilidade_rejeita_data_invalida_sem_erro_500(self):
        self._login("admin", "123456")
        resposta = self.client.get(
            "/api/disponibilidade?data_hora=invalida&servico_id=1&tipo_atendimento=Presencial&veterinario_id=1"
        )
        self.assertEqual(resposta.status_code, 400)
        self.assertIn("data e hora válidas", resposta.get_json()["mensagem"])

    def test_consultas_rejeita_mes_invalido_sem_erro_500(self):
        self._login("admin", "123456")
        resposta = self.client.get("/consultas?ano=2026&mes=13", follow_redirects=True)
        self.assertEqual(resposta.status_code, 200)
        self.assertIn("período informado não é válido", resposta.get_data(as_text=True))

    def test_criacao_consulta_rejeita_data_invalida_sem_erro_500(self):
        self._login("admin", "123456")
        resposta = self.client.post(
            "/consultas/nova",
            data={
                "data_hora": "invalida",
                "pet_id": self._id_pet(),
                "servico_id": self._id_servico(),
                "veterinario_id": self._id_veterinario("Veterinária Demo"),
                "tipo_atendimento": "Presencial",
                "status": "Agendada",
                "confirmacao_status": "Pendente",
            },
        )
        self.assertEqual(resposta.status_code, 200)
        self.assertIn("data e hora válidas", resposta.get_data(as_text=True))


if __name__ == "__main__":
    unittest.main()
