import sqlite3
import tempfile
import unittest
from pathlib import Path

import app as app_module
import init_db as init_db_module


class EstoqueMedicamentosTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "banco_teste_estoque.db"
        self.database_original_app = app_module.DATABASE
        self.database_original_init = init_db_module.DATABASE
        app_module.DATABASE = self.db_path
        init_db_module.DATABASE = self.db_path
        init_db_module.init_db()
        app_module.limpar_caches_referencia()
        app_module.app.config.update(TESTING=True)
        self.client = app_module.app.test_client()
        self._login_admin()

    def tearDown(self):
        app_module.DATABASE = self.database_original_app
        init_db_module.DATABASE = self.database_original_init
        app_module.limpar_caches_referencia()
        try:
            self.temp_dir.cleanup()
        except PermissionError:
            import gc, time
            gc.collect()
            time.sleep(0.1)
            try:
                self.temp_dir.cleanup()
            except Exception:
                pass

    def _conexao(self):
        c = sqlite3.connect(self.db_path)
        c.row_factory = sqlite3.Row
        return c

    def _login_admin(self):
        return self.client.post("/login", data={"login": "admin", "senha": "123456"}, follow_redirects=True)

    def _id_categoria(self, nome="Antibiotico"):
        c = self._conexao()
        r = c.execute("SELECT id FROM estoque_categorias WHERE nome=?", (nome,)).fetchone()
        c.close()
        return r["id"] if r else None

    def _id_fornecedor(self, nome="Distribuidora Vet Farma Ltda."):
        c = self._conexao()
        r = c.execute("SELECT id FROM estoque_fornecedores WHERE nome=?", (nome,)).fetchone()
        c.close()
        return r["id"] if r else None

    def _criar_produto(self, nome="TesteMed 10mg", qtd=20, qtd_min=10, valor=15.5, unidade="comprimido", validade="2027-12-31"):
        cat = self._id_categoria()
        forn = self._id_fornecedor()
        resp = self.client.post("/estoque/novo", data={
            "nome": nome,
            "categoria_id": cat,
            "fornecedor_id": forn,
            "quantidade_atual": str(qtd),
            "quantidade_minima": str(qtd_min),
            "data_validade": validade,
            "valor_compra": str(valor),
            "unidade_medida": unidade,
        }, follow_redirects=True)
        return resp

    def _criar_consulta_com_produtos(self, produto_qtds=None, status="Agendada"):
        # produto_qtds = [(produto_id, qtd), ...]
        c = self._conexao()
        pet_id = c.execute("SELECT id FROM pets LIMIT 1").fetchone()["id"]
        servico_id = c.execute("SELECT id FROM servicos LIMIT 1").fetchone()["id"]
        vet_id = c.execute("SELECT id FROM veterinarios LIMIT 1").fetchone()["id"]
        c.close()
        # usa data futura para evitar conflito
        import datetime
        data_hora = (datetime.datetime.now() + datetime.timedelta(days=5)).replace(hour=10, minute=0, second=0, microsecond=0).strftime("%Y-%m-%dT%H:%M")
        data = {
            "data_hora": data_hora,
            "pet_id": str(pet_id),
            "servico_id": str(servico_id),
            "veterinario_id": str(vet_id),
            "tipo_atendimento": "Presencial",
            "confirmacao_status": "Confirmada",
            "status": status,
            "observacoes": "teste",
            "diagnostico": "",
            "tratamento": "",
            "vacinas": "",
        }
        # adiciona produtos
        if produto_qtds:
            # flask test client precisa de listas para getlist: passar como multi dict
            # usa workaround: envia como lista de tuplas
            pass
        return data, pet_id, servico_id, vet_id

    # --- Cadastro ---
    def test_cadastro_produto_sucesso(self):
        resp = self._criar_produto(nome="NovoMedicamento X")
        self.assertIn("Produto cadastrado com sucesso", resp.get_data(as_text=True))
        c = self._conexao()
        row = c.execute("SELECT * FROM estoque_produtos WHERE nome=?", ("NovoMedicamento X",)).fetchone()
        c.close()
        self.assertIsNotNone(row)
        self.assertEqual(row["quantidade_atual"], 20)

    def test_cadastro_produto_nome_duplicado_falha(self):
        self._criar_produto(nome="Duplicado")
        resp = self._criar_produto(nome="Duplicado")
        self.assertIn("Já existe um produto com este nome", resp.get_data(as_text=True))

    def test_cadastro_unidade_invalida_falha(self):
        cat = self._id_categoria()
        forn = self._id_fornecedor()
        resp = self.client.post("/estoque/novo", data={
            "nome": "UnidadeInvalida",
            "categoria_id": cat,
            "fornecedor_id": forn,
            "quantidade_atual": "10",
            "quantidade_minima": "5",
            "data_validade": "2027-01-01",
            "valor_compra": "10",
            "unidade_medida": "tonelada",
        }, follow_redirects=True)
        self.assertIn("unidade de medida", resp.get_data(as_text=True).lower())

    def test_cadastro_quantidade_negativa_falha(self):
        cat = self._id_categoria()
        forn = self._id_fornecedor()
        resp = self.client.post("/estoque/novo", data={
            "nome": "Negativo",
            "categoria_id": cat,
            "fornecedor_id": forn,
            "quantidade_atual": "-5",
            "quantidade_minima": "2",
            "data_validade": "2027-01-01",
            "valor_compra": "10",
            "unidade_medida": "comprimido",
        }, follow_redirects=True)
        self.assertIn("não podem ser negativas", resp.get_data(as_text=True).lower())

    # --- Fornecedores inline / exclusão ---
    def test_fornecedor_inline_criacao_via_api(self):
        resp = self.client.post("/api/estoque/fornecedores", json={"nome": "Novo Fornecedor Teste", "contato": "(11) 9999-0000"})
        self.assertEqual(resp.status_code, 201)
        dados = resp.get_json()
        self.assertEqual(dados["fornecedor"]["nome"], "Novo Fornecedor Teste")
        # cria produto usando novo fornecedor
        cat = self._id_categoria()
        forn_id = dados["fornecedor"]["id"]
        resp2 = self.client.post("/estoque/novo", data={
            "nome": "ProdComNovoForn", "categoria_id": cat, "fornecedor_id": forn_id,
            "quantidade_atual": "10", "quantidade_minima": "2", "data_validade": "2027-01-01",
            "valor_compra": "10", "unidade_medida": "comprimido"
        }, follow_redirects=True)
        self.assertIn("Produto cadastrado", resp2.get_data(as_text=True))

    def test_exclusao_fornecedor_em_uso_bloqueia(self):
        # cria produto com fornecedor padrão
        self._criar_produto(nome="ProdFornUso", qtd=10)
        forn_id = self._id_fornecedor()
        # tenta excluir via API
        resp = self.client.delete(f"/api/estoque/fornecedores/{forn_id}")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("em uso", resp.get_json()["erro"].lower())
        # tenta via rota web
        resp2 = self.client.post(f"/estoque/fornecedores/{forn_id}/excluir", follow_redirects=True)
        self.assertIn("em uso", resp2.get_data(as_text=True).lower())
        # garante que fornecedor ainda existe
        c = self._conexao()
        row = c.execute("SELECT id FROM estoque_fornecedores WHERE id=?", (forn_id,)).fetchone()
        c.close()
        self.assertIsNotNone(row)

    def test_exclusao_fornecedor_sem_uso_permite(self):
        # cria fornecedor novo sem produtos
        resp = self.client.post("/api/estoque/fornecedores", json={"nome": "Fornecedor Livre", "contato": ""})
        forn_id = resp.get_json()["fornecedor"]["id"]
        resp2 = self.client.delete(f"/api/estoque/fornecedores/{forn_id}")
        self.assertEqual(resp2.status_code, 200)
        c = self._conexao()
        row = c.execute("SELECT id FROM estoque_fornecedores WHERE id=?", (forn_id,)).fetchone()
        c.close()
        self.assertIsNone(row)

    # --- Motivo renomeado venda -> uso ---
    def test_motivo_uso_renomeado(self):
        # verifica constante
        self.assertIn("uso", app_module.MOTIVOS_SAIDA_ESTOQUE)
        self.assertNotIn("venda", app_module.MOTIVOS_SAIDA_ESTOQUE)
        # saída com 'uso' deve funcionar
        self._criar_produto(nome="UsoTest", qtd=20)
        c = self._conexao()
        pid = c.execute("SELECT id FROM estoque_produtos WHERE nome=?", ("UsoTest",)).fetchone()["id"]
        c.close()
        resp = self.client.post("/estoque/saida", data={"produto_id": pid, "quantidade": "2", "motivo": "uso"}, follow_redirects=True)
        self.assertIn("Saída de 2", resp.get_data(as_text=True))
        c = self._conexao()
        mov = c.execute("SELECT motivo FROM estoque_movimentacoes WHERE produto_id=? ORDER BY id DESC LIMIT 1", (pid,)).fetchone()
        c.close()
        self.assertEqual(mov["motivo"], "uso")

    def test_motivo_venda_legado_aceito_e_normalizado(self):
        self._criar_produto(nome="VendaLegado", qtd=20)
        c = self._conexao()
        pid = c.execute("SELECT id FROM estoque_produtos WHERE nome=?", ("VendaLegado",)).fetchone()["id"]
        c.close()
        # envia 'venda' legado - deve ser aceito e normalizado para 'uso'
        resp = self.client.post("/estoque/saida", data={"produto_id": pid, "quantidade": "2", "motivo": "venda"}, follow_redirects=True)
        self.assertIn("Saída de 2", resp.get_data(as_text=True))
        c = self._conexao()
        mov = c.execute("SELECT motivo FROM estoque_movimentacoes WHERE produto_id=? ORDER BY id DESC LIMIT 1", (pid,)).fetchone()
        c.close()
        self.assertEqual(mov["motivo"], "uso")

    # --- Entrada ---
    def test_entrada_soma_estoque(self):
        self._criar_produto(nome="EntradaTest", qtd=10)
        c = self._conexao()
        pid = c.execute("SELECT id FROM estoque_produtos WHERE nome=?", ("EntradaTest",)).fetchone()["id"]
        c.close()
        resp = self.client.post("/estoque/entrada", data={
            "produto_id": pid, "quantidade": "5", "data_validade": "2028-01-01", "valor_compra": "20",
        }, follow_redirects=True)
        self.assertIn("Entrada de 5", resp.get_data(as_text=True))
        c = self._conexao()
        row = c.execute("SELECT quantidade_atual, valor_compra, data_validade FROM estoque_produtos WHERE id=?", (pid,)).fetchone()
        c.close()
        self.assertEqual(row["quantidade_atual"], 15)
        self.assertEqual(row["data_validade"], "2028-01-01")

    def test_entrada_quantidade_invalida_falha(self):
        self._criar_produto(nome="EntradaInvalida", qtd=10)
        c = self._conexao()
        pid = c.execute("SELECT id FROM estoque_produtos WHERE nome=?", ("EntradaInvalida",)).fetchone()["id"]
        c.close()
        resp = self.client.post("/estoque/entrada", data={"produto_id": pid, "quantidade": "0"}, follow_redirects=True)
        self.assertIn("quantidade válida", resp.get_data(as_text=True).lower())

    # --- Saída ---
    def test_saida_subtrai_estoque(self):
        self._criar_produto(nome="SaidaTest", qtd=20, qtd_min=5)
        c = self._conexao()
        pid = c.execute("SELECT id FROM estoque_produtos WHERE nome=?", ("SaidaTest",)).fetchone()["id"]
        tid = c.execute("SELECT id FROM tutores LIMIT 1").fetchone()["id"]
        c.close()
        resp = self.client.post("/estoque/saida", data={"produto_id": pid, "quantidade": "8", "cliente_tutor_id": tid, "motivo": "uso"}, follow_redirects=True)
        self.assertIn("Saída de 8", resp.get_data(as_text=True))
        c = self._conexao()
        row = c.execute("SELECT quantidade_atual FROM estoque_produtos WHERE id=?", (pid,)).fetchone()
        c.close()
        self.assertEqual(row["quantidade_atual"], 12)

    def test_saida_maior_que_estoque_falha(self):
        self._criar_produto(nome="SaidaFalha", qtd=3)
        c = self._conexao()
        pid = c.execute("SELECT id FROM estoque_produtos WHERE nome=?", ("SaidaFalha",)).fetchone()["id"]
        c.close()
        resp = self.client.post("/estoque/saida", data={"produto_id": pid, "quantidade": "10", "motivo": "uso"}, follow_redirects=True)
        texto = resp.get_data(as_text=True)
        self.assertIn("Quantidade insuficiente", texto)
        c = self._conexao()
        row = c.execute("SELECT quantidade_atual FROM estoque_produtos WHERE id=?", (pid,)).fetchone()
        c.close()
        self.assertEqual(row["quantidade_atual"], 3)

    def test_saida_motivo_invalido_falha(self):
        self._criar_produto(nome="MotivoInvalido", qtd=10)
        c = self._conexao()
        pid = c.execute("SELECT id FROM estoque_produtos WHERE nome=?", ("MotivoInvalido",)).fetchone()["id"]
        c.close()
        resp = self.client.post("/estoque/saida", data={"produto_id": pid, "quantidade": "2", "motivo": "roubo"}, follow_redirects=True)
        self.assertIn("Motivo da saída inválido", resp.get_data(as_text=True))

    def test_saida_gera_alerta_reposicao(self):
        self._criar_produto(nome="AlertaTest", qtd=10, qtd_min=8)
        c = self._conexao()
        pid = c.execute("SELECT id FROM estoque_produtos WHERE nome=?", ("AlertaTest",)).fetchone()["id"]
        c.close()
        resp = self.client.post("/estoque/saida", data={"produto_id": pid, "quantidade": "5", "motivo": "uso"}, follow_redirects=True)
        texto = resp.get_data(as_text=True)
        self.assertIn("Alerta", texto)

    def test_api_validar_saida(self):
        self._criar_produto(nome="ApiValida", qtd=10)
        c = self._conexao()
        pid = c.execute("SELECT id FROM estoque_produtos WHERE nome=?", ("ApiValida",)).fetchone()["id"]
        c.close()
        resp = self.client.get(f"/api/estoque/validar-saida?produto_id={pid}&quantidade=5")
        dados = resp.get_json()
        self.assertTrue(dados["valido"])
        resp2 = self.client.get(f"/api/estoque/validar-saida?produto_id={pid}&quantidade=20")
        dados2 = resp2.get_json()
        self.assertFalse(dados2["valido"])
        self.assertIn("insuficiente", dados2["mensagem"].lower())

    def test_api_crud_produto(self):
        cat = self._id_categoria()
        forn = self._id_fornecedor()
        resp = self.client.post("/api/estoque/produtos", json={
            "nome": "ApiCrud", "categoria_id": cat, "fornecedor_id": forn,
            "quantidade_atual": 7, "quantidade_minima": 3,
            "data_validade": "2027-05-01", "valor_compra": 12.5, "unidade_medida": "ml",
        })
        self.assertEqual(resp.status_code, 201)
        pid = resp.get_json()["produto"]["id"]
        resp2 = self.client.get(f"/api/estoque/produtos/{pid}")
        self.assertEqual(resp2.status_code, 200)
        resp3 = self.client.put(f"/api/estoque/produtos/{pid}", json={"quantidade_atual": 15})
        self.assertEqual(resp3.status_code, 200)
        self.assertEqual(resp3.get_json()["produto"]["quantidade_atual"], 15)
        resp4 = self.client.delete(f"/api/estoque/produtos/{pid}")
        self.assertEqual(resp4.status_code, 200)
        c = self._conexao()
        row = c.execute("SELECT id FROM estoque_produtos WHERE id=?", (pid,)).fetchone()
        c.close()
        self.assertIsNone(row)

    def test_api_alertas(self):
        self._criar_produto(nome="AlertaApi", qtd=5, qtd_min=5)
        resp = self.client.get("/api/estoque/alertas")
        dados = resp.get_json()
        self.assertIn("alertas_reposicao", dados)
        nomes = [p["nome"] for p in dados["alertas_reposicao"]]
        self.assertIn("AlertaApi", nomes)

    def test_historico_movimentacoes(self):
        self._criar_produto(nome="HistTest", qtd=10)
        c = self._conexao()
        pid = c.execute("SELECT id FROM estoque_produtos WHERE nome=?", ("HistTest",)).fetchone()["id"]
        c.close()
        self.client.post("/estoque/entrada", data={"produto_id": pid, "quantidade": "5"}, follow_redirects=True)
        self.client.post("/estoque/saida", data={"produto_id": pid, "quantidade": "3", "motivo": "uso"}, follow_redirects=True)
        c = self._conexao()
        movs = c.execute("SELECT COUNT(*) FROM estoque_movimentacoes WHERE produto_id=?", (pid,)).fetchone()[0]
        c.close()
        self.assertEqual(movs, 2)

    # --- Consulta + Estoque (integração) ---
    def _criar_produto_e_get_id(self, nome, qtd):
        self._criar_produto(nome=nome, qtd=qtd)
        c = self._conexao()
        pid = c.execute("SELECT id FROM estoque_produtos WHERE nome=?", (nome,)).fetchone()["id"]
        c.close()
        return pid

    def _dados_consulta_base(self, status="Agendada"):
        import datetime
        c = self._conexao()
        pet_id = c.execute("SELECT id FROM pets LIMIT 1").fetchone()["id"]
        servico_id = c.execute("SELECT id FROM servicos LIMIT 1").fetchone()["id"]
        vet_id = c.execute("SELECT id FROM veterinarios LIMIT 1").fetchone()["id"]
        c.close()
        # usa horário futuro único para evitar conflito
        base = datetime.datetime.now() + datetime.timedelta(days=10, hours=2)
        # garante horário dentro do expediente
        base = base.replace(hour=10, minute=0, second=0, microsecond=0)
        return {
            "data_hora": base.strftime("%Y-%m-%dT%H:%M"),
            "pet_id": str(pet_id),
            "servico_id": str(servico_id),
            "veterinario_id": str(vet_id),
            "tipo_atendimento": "Presencial",
            "confirmacao_status": "Confirmada",
            "status": status,
            "observacoes": "obs",
            "diagnostico": "",
            "tratamento": "",
            "vacinas": "",
        }

    def test_consulta_pendente_nao_desconta_estoque(self):
        pid = self._criar_produto_e_get_id("ProdPend", 20)
        dados = self._dados_consulta_base(status="Agendada")
        dados["produto_estoque_id"] = [str(pid)]
        dados["produto_estoque_qtd"] = ["5"]
        # cria consulta Agendada com produto
        resp = self.client.post("/consultas/nova", data=dados, follow_redirects=True)
        self.assertIn("cadastrada com sucesso", resp.get_data(as_text=True).lower())
        c = self._conexao()
        qtd = c.execute("SELECT quantidade_atual FROM estoque_produtos WHERE id=?", (pid,)).fetchone()["quantidade_atual"]
        mov = c.execute("SELECT COUNT(*) FROM estoque_movimentacoes WHERE produto_id=?", (pid,)).fetchone()[0]
        consulta_id = c.execute("SELECT id FROM consultas ORDER BY id DESC LIMIT 1").fetchone()["id"]
        vinc = c.execute("SELECT COUNT(*) FROM consulta_produtos WHERE consulta_id=?", (consulta_id,)).fetchone()[0]
        c.close()
        self.assertEqual(qtd, 20)  # não descontou
        self.assertEqual(mov, 0)
        self.assertEqual(vinc, 1)

    def test_consulta_concluida_desconta_estoque(self):
        pid = self._criar_produto_e_get_id("ProdConcl", 20)
        dados = self._dados_consulta_base(status="Agendada")
        # cria Agendada primeiro
        dados["produto_estoque_id"] = [str(pid)]
        dados["produto_estoque_qtd"] = ["6"]
        self.client.post("/consultas/nova", data=dados, follow_redirects=True)
        c = self._conexao()
        consulta_id = c.execute("SELECT id FROM consultas ORDER BY id DESC LIMIT 1").fetchone()["id"]
        c.close()
        # edita para Concluida
        dados_editar = self._dados_consulta_base(status="Concluida")
        dados_editar["produto_estoque_id"] = [str(pid)]
        dados_editar["produto_estoque_qtd"] = ["6"]
        # precisa manter mesma data_hora para não conflitar? usa mesma data_hora do original + mantém
        c = self._conexao()
        consulta = c.execute("SELECT data_hora FROM consultas WHERE id=?", (consulta_id,)).fetchone()
        c.close()
        dados_editar["data_hora"] = consulta["data_hora"]
        resp = self.client.post(f"/consultas/{consulta_id}/editar", data=dados_editar, follow_redirects=True)
        self.assertIn("atualizada com sucesso", resp.get_data(as_text=True).lower())
        c = self._conexao()
        qtd = c.execute("SELECT quantidade_atual FROM estoque_produtos WHERE id=?", (pid,)).fetchone()["quantidade_atual"]
        mov = c.execute("SELECT * FROM estoque_movimentacoes WHERE produto_id=? AND consulta_id=?", (pid, consulta_id)).fetchone()
        c.close()
        self.assertEqual(qtd, 14)
        self.assertIsNotNone(mov)
        self.assertEqual(mov["motivo"], "uso")
        self.assertEqual(mov["quantidade"], 6)

    def test_consulta_estoque_insuficiente_bloqueia_conclusao(self):
        pid = self._criar_produto_e_get_id("ProdInsuf", 3)
        dados = self._dados_consulta_base(status="Agendada")
        dados["produto_estoque_id"] = [str(pid)]
        dados["produto_estoque_qtd"] = ["10"]  # maior que estoque
        self.client.post("/consultas/nova", data=dados, follow_redirects=True)
        c = self._conexao()
        consulta_id = c.execute("SELECT id FROM consultas ORDER BY id DESC LIMIT 1").fetchone()["id"]
        consulta = c.execute("SELECT data_hora FROM consultas WHERE id=?", (consulta_id,)).fetchone()
        c.close()
        dados_editar = self._dados_consulta_base(status="Concluida")
        dados_editar["data_hora"] = consulta["data_hora"]
        dados_editar["produto_estoque_id"] = [str(pid)]
        dados_editar["produto_estoque_qtd"] = ["10"]
        resp = self.client.post(f"/consultas/{consulta_id}/editar", data=dados_editar, follow_redirects=True)
        texto = resp.get_data(as_text=True)
        self.assertIn("Estoque insuficiente", texto)
        c = self._conexao()
        qtd = c.execute("SELECT quantidade_atual FROM estoque_produtos WHERE id=?", (pid,)).fetchone()["quantidade_atual"]
        status = c.execute("SELECT status FROM consultas WHERE id=?", (consulta_id,)).fetchone()["status"]
        c.close()
        self.assertEqual(qtd, 3)  # não descontou
        self.assertNotEqual(status, "Concluida")

    def test_consulta_cancelada_nao_desconta(self):
        pid = self._criar_produto_e_get_id("ProdCancel", 15)
        dados = self._dados_consulta_base(status="Cancelada")
        dados["produto_estoque_id"] = [str(pid)]
        dados["produto_estoque_qtd"] = ["5"]
        resp = self.client.post("/consultas/nova", data=dados, follow_redirects=True)
        self.assertIn("cadastrada", resp.get_data(as_text=True).lower())
        c = self._conexao()
        qtd = c.execute("SELECT quantidade_atual FROM estoque_produtos WHERE id=?", (pid,)).fetchone()["quantidade_atual"]
        mov = c.execute("SELECT COUNT(*) FROM estoque_movimentacoes WHERE produto_id=?", (pid,)).fetchone()[0]
        c.close()
        self.assertEqual(qtd, 15)
        self.assertEqual(mov, 0)

    def test_consulta_concluida_nao_duplica_saida(self):
        pid = self._criar_produto_e_get_id("ProdDupl", 20)
        dados = self._dados_consulta_base(status="Concluida")
        dados["produto_estoque_id"] = [str(pid)]
        dados["produto_estoque_qtd"] = ["4"]
        self.client.post("/consultas/nova", data=dados, follow_redirects=True)
        c = self._conexao()
        consulta_id = c.execute("SELECT id FROM consultas ORDER BY id DESC LIMIT 1").fetchone()["id"]
        qtd1 = c.execute("SELECT quantidade_atual FROM estoque_produtos WHERE id=?", (pid,)).fetchone()["quantidade_atual"]
        consulta = c.execute("SELECT * FROM consultas WHERE id=?", (consulta_id,)).fetchone()
        c.close()
        self.assertEqual(qtd1, 16)
        # edita novamente mantendo Concluida - não deve descontar de novo
        dados_editar = self._dados_consulta_base(status="Concluida")
        c = self._conexao()
        consulta = c.execute("SELECT data_hora FROM consultas WHERE id=?", (consulta_id,)).fetchone()
        c.close()
        dados_editar["data_hora"] = consulta["data_hora"]
        dados_editar["produto_estoque_id"] = [str(pid)]
        dados_editar["produto_estoque_qtd"] = ["4"]
        resp = self.client.post(f"/consultas/{consulta_id}/editar", data=dados_editar, follow_redirects=True)
        self.assertIn("atualizada", resp.get_data(as_text=True).lower())
        c = self._conexao()
        qtd2 = c.execute("SELECT quantidade_atual FROM estoque_produtos WHERE id=?", (pid,)).fetchone()["quantidade_atual"]
        mov_count = c.execute("SELECT COUNT(*) FROM estoque_movimentacoes WHERE consulta_id=?", (consulta_id,)).fetchone()[0]
        c.close()
        self.assertEqual(qtd2, 16)  # não descontou novamente
        self.assertEqual(mov_count, 1)

    def test_rastreabilidade_consulta_movimentacao(self):
        pid = self._criar_produto_e_get_id("ProdRastr", 20)
        dados = self._dados_consulta_base(status="Concluida")
        dados["produto_estoque_id"] = [str(pid)]
        dados["produto_estoque_qtd"] = ["3"]
        self.client.post("/consultas/nova", data=dados, follow_redirects=True)
        c = self._conexao()
        consulta_id = c.execute("SELECT id FROM consultas ORDER BY id DESC LIMIT 1").fetchone()["id"]
        mov = c.execute("SELECT consulta_id, motivo FROM estoque_movimentacoes WHERE produto_id=? AND consulta_id=?", (pid, consulta_id)).fetchone()
        # historico do produto deve conter link
        hist = c.execute("SELECT * FROM estoque_movimentacoes WHERE produto_id=?", (pid,)).fetchall()
        c.close()
        self.assertIsNotNone(mov)
        self.assertEqual(mov["consulta_id"], consulta_id)
        self.assertEqual(mov["motivo"], "uso")
        self.assertTrue(len(hist) >= 1)


if __name__ == "__main__":
    unittest.main()
