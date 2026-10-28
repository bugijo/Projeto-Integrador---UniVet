"""Exclusões e edição cadastral sem perda de histórico do estoque."""
import unittest

import test_app as fixtures


class StockMaintenanceTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.UniVetAppTests()
        self.fixture.setUp()
        self.client = self.fixture.client
        self.fixture._login("admin", "123456")

    def tearDown(self):
        self.fixture.tearDown()

    def _produto(self, nome):
        response = self.client.post("/estoque/produtos/novo", data={
            "nome": nome, "codigo": nome.upper().replace(" ", "-"),
            "tipo": "Material", "unidade_medida": "unidade",
            "estoque_minimo": "0", "margem_lucro_percentual": "30",
        })
        self.assertEqual(response.status_code, 302)
        with self.fixture._conexao() as conn:
            return conn.execute("SELECT id FROM produtos WHERE nome = ?", (nome,)).fetchone()["id"]

    def _lote_sem_historico(self, produto_id, numero, saldo=0):
        with self.fixture._conexao() as conn:
            fornecedor_id = conn.execute("SELECT id FROM fornecedores ORDER BY id LIMIT 1").fetchone()["id"]
            cursor = conn.execute(
                """INSERT INTO lotes
                   (produto_id, fornecedor_id, numero_lote, quantidade_inicial,
                    quantidade_atual, validade, valor_compra_unitario, data_entrada)
                   VALUES (?, ?, ?, 1, ?, '2099-12-31', 10, '2026-10-28')""",
                (produto_id, fornecedor_id, numero, saldo),
            )
            return cursor.lastrowid

    def _entrada(self, produto_id):
        with self.fixture._conexao() as conn:
            fornecedor_id = conn.execute("SELECT id FROM fornecedores ORDER BY id LIMIT 1").fetchone()["id"]
        response = self.client.post("/estoque/lotes/entrada", data={
            "produto_id": str(produto_id), "fornecedor_id": str(fornecedor_id),
            "numero_lote": "ENTRADA-HISTORICA", "quantidade": "3",
            "validade": "2099-12-31", "valor_compra_unitario": "10",
            "motivo": "Entrada fictícia de teste",
        })
        self.assertEqual(response.status_code, 302)
        with self.fixture._conexao() as conn:
            return conn.execute(
                "SELECT id FROM lotes WHERE produto_id = ? AND numero_lote = ?",
                (produto_id, "ENTRADA-HISTORICA"),
            ).fetchone()["id"]

    def _consulta(self):
        with self.fixture._conexao() as conn:
            return conn.execute("SELECT id FROM consultas ORDER BY id LIMIT 1").fetchone()["id"]

    def test_product_without_references_can_be_deleted_only_with_confirmation(self):
        product_id = self._produto("Produto removível fictício")

        response = self.client.post(f"/estoque/produtos/{product_id}/excluir", data={}, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Confirme a exclusão", response.get_data(as_text=True))
        with self.fixture._conexao() as conn:
            self.assertIsNotNone(conn.execute("SELECT id FROM produtos WHERE id = ?", (product_id,)).fetchone())

        response = self.client.post(
            f"/estoque/produtos/{product_id}/excluir", data={"confirmar_exclusao": "sim"}
        )
        self.assertEqual(response.status_code, 302)
        with self.fixture._conexao() as conn:
            self.assertIsNone(conn.execute("SELECT id FROM produtos WHERE id = ?", (product_id,)).fetchone())

    def test_product_delete_is_post_csrf_and_admin_only(self):
        product_id = self._produto("Produto protegido fictício")
        get_response = self.client.get(f"/estoque/produtos/{product_id}/excluir")
        self.assertNotEqual(get_response.status_code, 200)
        with self.fixture._conexao() as conn:
            self.assertIsNotNone(conn.execute("SELECT id FROM produtos WHERE id = ?", (product_id,)).fetchone())
        self.assertEqual(self.client.post(
            f"/estoque/produtos/{product_id}/excluir",
            data={"csrf_token": "", "confirmar_exclusao": "sim"},
        ).status_code, 400)

        self.client.post("/logout", follow_redirects=True)
        self.fixture._login("vet.demo", "Fer123")
        self.assertEqual(self.client.post(
            f"/estoque/produtos/{product_id}/excluir", data={"confirmar_exclusao": "sim"}
        ).status_code, 403)
        with self.fixture._conexao() as conn:
            self.assertIsNotNone(conn.execute("SELECT id FROM produtos WHERE id = ?", (product_id,)).fetchone())

    def test_product_with_empty_lot_cannot_be_deleted_and_can_be_deactivated(self):
        product_id = self._produto("Produto com lote fictício")
        self._lote_sem_historico(product_id, "LOTE-SEM-MOVIMENTO")
        response = self.client.post(
            f"/estoque/produtos/{product_id}/excluir", data={"confirmar_exclusao": "sim"}, follow_redirects=True
        )
        self.assertIn("possui histórico de estoque e não pode ser excluído", response.get_data(as_text=True))
        response = self.client.post(f"/estoque/produtos/{product_id}/alternar")
        self.assertEqual(response.status_code, 302)
        with self.fixture._conexao() as conn:
            product = conn.execute("SELECT ativo FROM produtos WHERE id = ?", (product_id,)).fetchone()
            self.assertEqual(product["ativo"], 0)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM lotes WHERE produto_id = ?", (product_id,)).fetchone()[0], 1)

    def test_product_with_movement_cannot_be_deleted(self):
        product_id = self._produto("Produto movimentado fictício")
        self._entrada(product_id)
        response = self.client.post(
            f"/estoque/produtos/{product_id}/excluir", data={"confirmar_exclusao": "sim"}, follow_redirects=True
        )
        self.assertIn("possui histórico de estoque e não pode ser excluído", response.get_data(as_text=True))
        with self.fixture._conexao() as conn:
            self.assertIsNotNone(conn.execute("SELECT id FROM produtos WHERE id = ?", (product_id,)).fetchone())
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM movimentacoes_estoque WHERE produto_id = ?", (product_id,)).fetchone()[0], 1)

    def test_product_screens_show_delete_or_traceability_block(self):
        empty_product = self._produto("Produto vazio visível fictício")
        page = self.client.get("/estoque/produtos")
        self.assertEqual(page.status_code, 200)
        self.assertIn("Excluir", page.get_data(as_text=True))
        detail = self.client.get(f"/estoque/produtos/{empty_product}")
        self.assertEqual(detail.status_code, 200)
        self.assertIn("Esta ação não poderá ser desfeita", detail.get_data(as_text=True))

        historic = self.client.get("/estoque/produtos/1")
        self.assertEqual(historic.status_code, 200)
        self.assertIn("Utilize Desativar para preservar a rastreabilidade", historic.get_data(as_text=True))

    def test_product_used_by_consultation_cannot_be_deleted(self):
        product_id = self._produto("Produto vinculado consulta fictício")
        lot_id = self._lote_sem_historico(product_id, "LOTE-CONSULTA")
        with self.fixture._conexao() as conn:
            conn.execute(
                "INSERT INTO itens_consulta (consulta_id, produto_id, lote_id, quantidade) VALUES (?, ?, ?, 1)",
                (self._consulta(), product_id, lot_id),
            )
        response = self.client.post(
            f"/estoque/produtos/{product_id}/excluir", data={"confirmar_exclusao": "sim"}, follow_redirects=True
        )
        self.assertIn("possui histórico de estoque e não pode ser excluído", response.get_data(as_text=True))
        with self.fixture._conexao() as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM itens_consulta WHERE produto_id = ?", (product_id,)).fetchone()[0], 1)

    def test_lot_without_history_can_change_product_and_be_deleted(self):
        first_product = self._produto("Produto lote origem fictício")
        second_product = self._produto("Produto lote destino fictício")
        lot_id = self._lote_sem_historico(first_product, "LOTE-CORRIGIVEL")

        response = self.client.post(f"/estoque/lotes/{lot_id}/editar", data={
            "produto_id": str(second_product), "numero_lote": "LOTE-CORRIGIDO",
            "validade": "2098-11-30", "fornecedor_id": "",
        })
        self.assertEqual(response.status_code, 302)
        with self.fixture._conexao() as conn:
            lot = conn.execute("SELECT produto_id, numero_lote, validade FROM lotes WHERE id = ?", (lot_id,)).fetchone()
            self.assertEqual((lot["produto_id"], lot["numero_lote"], lot["validade"]), (second_product, "LOTE-CORRIGIDO", "2098-11-30"))
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM movimentacoes_estoque WHERE lote_id = ?", (lot_id,)).fetchone()[0], 0)

        response = self.client.post(f"/estoque/lotes/{lot_id}/excluir", data={}, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Confirme a exclusão", response.get_data(as_text=True))
        response = self.client.post(f"/estoque/lotes/{lot_id}/excluir", data={"confirmar_exclusao": "sim"})
        self.assertEqual(response.status_code, 302)
        with self.fixture._conexao() as conn:
            self.assertIsNone(conn.execute("SELECT id FROM lotes WHERE id = ?", (lot_id,)).fetchone())

    def test_lot_with_movement_cannot_change_product_or_be_deleted(self):
        first_product = self._produto("Produto lote histórico A")
        second_product = self._produto("Produto lote histórico B")
        lot_id = self._entrada(first_product)
        with self.fixture._conexao() as conn:
            movement_count = conn.execute("SELECT COUNT(*) FROM movimentacoes_estoque WHERE lote_id = ?", (lot_id,)).fetchone()[0]

        response = self.client.post(f"/estoque/lotes/{lot_id}/editar", data={
            "produto_id": str(second_product), "numero_lote": "LOTE-HISTORICO",
            "validade": "2099-12-31", "fornecedor_id": "",
        }, follow_redirects=True)
        self.assertIn("produto deste lote não pode ser alterado porque já existem movimentações", response.get_data(as_text=True))
        response = self.client.post(
            f"/estoque/lotes/{lot_id}/excluir", data={"confirmar_exclusao": "sim"}, follow_redirects=True
        )
        self.assertIn("possui movimentações e não pode ser excluído", response.get_data(as_text=True))
        with self.fixture._conexao() as conn:
            lot = conn.execute("SELECT produto_id FROM lotes WHERE id = ?", (lot_id,)).fetchone()
            self.assertEqual(lot["produto_id"], first_product)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM movimentacoes_estoque WHERE lote_id = ?", (lot_id,)).fetchone()[0], movement_count)

    def test_lot_with_consultation_item_cannot_change_product_or_be_deleted(self):
        first_product = self._produto("Produto consulta lote A")
        second_product = self._produto("Produto consulta lote B")
        lot_id = self._lote_sem_historico(first_product, "LOTE-ITEM-CONSULTA")
        with self.fixture._conexao() as conn:
            conn.execute(
                "INSERT INTO itens_consulta (consulta_id, produto_id, lote_id, quantidade) VALUES (?, ?, ?, 1)",
                (self._consulta(), first_product, lot_id),
            )

        response = self.client.post(f"/estoque/lotes/{lot_id}/editar", data={
            "produto_id": str(second_product), "numero_lote": "LOTE-ITEM-CONSULTA",
            "validade": "2099-12-31", "fornecedor_id": "",
        }, follow_redirects=True)
        self.assertIn("produto deste lote não pode ser alterado", response.get_data(as_text=True))
        response = self.client.post(
            f"/estoque/lotes/{lot_id}/excluir", data={"confirmar_exclusao": "sim"}, follow_redirects=True
        )
        self.assertIn("possui movimentações e não pode ser excluído", response.get_data(as_text=True))
        with self.fixture._conexao() as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM itens_consulta WHERE lote_id = ?", (lot_id,)).fetchone()[0], 1)

    def test_lot_with_balance_but_no_history_cannot_be_deleted(self):
        product_id = self._produto("Produto saldo legado fictício")
        lot_id = self._lote_sem_historico(product_id, "LOTE-SALDO-SEM-MOVIMENTO", saldo=2)
        response = self.client.post(
            f"/estoque/lotes/{lot_id}/excluir", data={"confirmar_exclusao": "sim"}, follow_redirects=True
        )
        self.assertIn("saldo atual e não pode ser excluído", response.get_data(as_text=True))
        with self.fixture._conexao() as conn:
            self.assertEqual(conn.execute("SELECT quantidade_atual FROM lotes WHERE id = ?", (lot_id,)).fetchone()[0], 2)

    def test_lot_edit_delete_require_post_csrf_and_admin(self):
        product_id = self._produto("Produto proteção lote fictício")
        lot_id = self._lote_sem_historico(product_id, "LOTE-PROTEGIDO")
        self.assertNotEqual(self.client.get(f"/estoque/lotes/{lot_id}/excluir").status_code, 200)
        with self.fixture._conexao() as conn:
            self.assertIsNotNone(conn.execute("SELECT id FROM lotes WHERE id = ?", (lot_id,)).fetchone())
        self.assertEqual(self.client.post(
            f"/estoque/lotes/{lot_id}/excluir",
            data={"csrf_token": "", "confirmar_exclusao": "sim"},
        ).status_code, 400)

        self.client.post("/logout", follow_redirects=True)
        self.fixture._login("vet.demo", "Fer123")
        self.assertEqual(self.client.post(f"/estoque/lotes/{lot_id}/excluir", data={"confirmar_exclusao": "sim"}).status_code, 403)
        self.assertEqual(self.client.post(f"/estoque/lotes/{lot_id}/editar", data={
            "produto_id": str(product_id), "numero_lote": "LOTE-PROTEGIDO-ALTERADO",
            "validade": "2099-12-31", "fornecedor_id": "",
        }).status_code, 403)
        with self.fixture._conexao() as conn:
            self.assertEqual(conn.execute("SELECT numero_lote FROM lotes WHERE id = ?", (lot_id,)).fetchone()[0], "LOTE-PROTEGIDO")

    def test_lot_screen_separates_edit_adjustment_and_delete(self):
        product_id = self._produto("Produto ações lote fictício")
        empty_lot = self._lote_sem_historico(product_id, "LOTE-SEM-HISTORICO-UI")
        historical_product = self._produto("Produto lote histórico UI fictício")
        historical_lot = self._entrada(historical_product)

        page = self.client.get("/estoque/lotes")
        body = page.get_data(as_text=True)
        self.assertEqual(page.status_code, 200)
        self.assertIn("Editar dados", body)
        self.assertIn("Ajustar estoque", body)
        self.assertIn(f"/estoque/lotes/{empty_lot}/excluir", body)
        self.assertIn("Este lote possui movimentações e não pode ser excluído", body)

        form = self.client.get(f"/estoque/lotes/{historical_lot}/editar")
        self.assertEqual(form.status_code, 200)
        self.assertIn("O produto deste lote não pode ser alterado", form.get_data(as_text=True))

    def test_cadastral_lot_edit_does_not_create_fake_movement_and_adjustment_remains_audited(self):
        product_id = self._produto("Produto ajuste após edição fictício")
        lot_id = self._entrada(product_id)
        with self.fixture._conexao() as conn:
            before_count = conn.execute("SELECT COUNT(*) FROM movimentacoes_estoque WHERE lote_id = ?", (lot_id,)).fetchone()[0]
        response = self.client.post(f"/estoque/lotes/{lot_id}/editar", data={
            "produto_id": str(product_id), "numero_lote": "LOTE-CADASTRAL-EDITADO",
            "validade": "2098-12-31", "fornecedor_id": "",
        })
        self.assertEqual(response.status_code, 302)
        with self.fixture._conexao() as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM movimentacoes_estoque WHERE lote_id = ?", (lot_id,)).fetchone()[0], before_count)

        response = self.client.post(f"/estoque/lotes/{lot_id}/ajuste", data={
            "nova_quantidade": "2", "motivo": "Conferência fictícia após edição cadastral",
        })
        self.assertEqual(response.status_code, 302)
        with self.fixture._conexao() as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM movimentacoes_estoque WHERE lote_id = ?", (lot_id,)).fetchone()[0], before_count + 1)
            movement = conn.execute("SELECT tipo, motivo FROM movimentacoes_estoque WHERE lote_id = ? ORDER BY id DESC LIMIT 1", (lot_id,)).fetchone()
            self.assertEqual((movement["tipo"], movement["motivo"]), ("Ajuste", "Conferência fictícia após edição cadastral (redução)"))


if __name__ == "__main__":
    unittest.main()
