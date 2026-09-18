import sqlite3
import tempfile
import unittest
from pathlib import Path

from estoque.schema import criar_tabelas_estoque
from estoque.services import (
    EstoqueInsuficiente,
    consumo_por_produto,
    listar_produtos,
    registrar_entrada,
    registrar_estorno,
    registrar_saida_fefo,
    registrar_uso_consulta,
    resumo_estoque,
)


class EstoqueServicesTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.connection = sqlite3.connect(Path(self.temp_dir.name) / "estoque.db")
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.executescript(
            """
            CREATE TABLE usuarios (id INTEGER PRIMARY KEY, nome TEXT);
            CREATE TABLE consultas (id INTEGER PRIMARY KEY, pet_id INTEGER);
            INSERT INTO usuarios (id, nome) VALUES (1, 'Usuário teste');
            INSERT INTO consultas (id, pet_id) VALUES (1, 1);
            """
        )
        criar_tabelas_estoque(self.connection)
        self.categoria_id = self.connection.execute("INSERT INTO categorias (nome) VALUES ('Medicamentos')").lastrowid
        self.fornecedor_id = self.connection.execute("INSERT INTO fornecedores (nome) VALUES ('Fornecedor teste')").lastrowid
        self.produto_id = self.connection.execute(
            """
            INSERT INTO produtos (nome, codigo, tipo, categoria_id, unidade_medida, estoque_minimo)
            VALUES ('Produto teste', 'TEST-001', 'Medicamento', ?, 'unidade', 5)
            """,
            (self.categoria_id,),
        ).lastrowid
        self.connection.commit()

    def tearDown(self):
        self.connection.close()
        self.temp_dir.cleanup()

    def entrada(self, lote, quantidade, validade):
        return registrar_entrada(self.connection, self.produto_id, self.fornecedor_id, lote, quantidade, validade, 10, 1)

    def saldo(self):
        return self.connection.execute("SELECT COALESCE(SUM(quantidade_atual), 0) FROM lotes").fetchone()[0]

    def test_cadastro_de_produto_e_alerta_de_estoque_minimo(self):
        self.entrada("L-001", 2, "2027-12-31")
        produto = listar_produtos(self.connection, {"situacao": "baixo", "somente_ativos": True})
        self.assertEqual([item["id"] for item in produto], [self.produto_id])
        self.assertEqual(resumo_estoque(self.connection)["baixo"], 1)

    def test_entrada_cria_lote_e_movimentacao(self):
        lote_id, movement_id = self.entrada("L-001", 10, "2027-12-31")
        lote = self.connection.execute("SELECT quantidade_atual FROM lotes WHERE id = ?", (lote_id,)).fetchone()
        movement = self.connection.execute("SELECT tipo, quantidade FROM movimentacoes_estoque WHERE id = ?", (movement_id,)).fetchone()
        self.assertEqual(lote["quantidade_atual"], 10)
        self.assertEqual((movement["tipo"], movement["quantidade"]), ("Entrada", 10))

    def test_valor_sugerido_por_lote_e_valor_praticado_na_saida(self):
        lote_id, _ = self.entrada("L-001", 10, "2027-12-31")
        lote = self.connection.execute(
            "SELECT valor_compra_unitario, valor_venda_sugerido_unitario FROM lotes WHERE id = ?",
            (lote_id,),
        ).fetchone()
        self.assertEqual((lote["valor_compra_unitario"], lote["valor_venda_sugerido_unitario"]), (10, 13))

        saida = registrar_saida_fefo(self.connection, self.produto_id, 2, 1, valor_unitario_praticado=15)[0]
        movimento = self.connection.execute(
            "SELECT valor_unitario_sugerido, valor_unitario_praticado FROM movimentacoes_estoque WHERE id = ?",
            (saida["movimentacao_id"],),
        ).fetchone()
        self.assertEqual((movimento["valor_unitario_sugerido"], movimento["valor_unitario_praticado"]), (13, 15))

    def test_valor_praticado_fica_registrado_no_uso_da_consulta(self):
        self.entrada("L-001", 5, "2027-12-31")
        registrar_uso_consulta(self.connection, 1, self.produto_id, 2, 1, valor_unitario_praticado=18)
        item = self.connection.execute(
            "SELECT valor_unitario_sugerido, valor_unitario_praticado FROM itens_consulta WHERE consulta_id = 1"
        ).fetchone()
        self.assertEqual((item["valor_unitario_sugerido"], item["valor_unitario_praticado"]), (13, 18))

    def test_saida_nao_permite_estoque_negativo(self):
        self.entrada("L-001", 2, "2027-12-31")
        with self.assertRaises(EstoqueInsuficiente):
            registrar_saida_fefo(self.connection, self.produto_id, 3, 1)
        self.assertEqual(self.saldo(), 2)

    def test_lote_vencido_nao_eh_selecionado(self):
        self.entrada("VENCIDO", 10, "2020-01-01")
        self.entrada("VALIDO", 2, "2027-12-31")
        with self.assertRaises(EstoqueInsuficiente):
            registrar_saida_fefo(self.connection, self.produto_id, 3, 1)
        vencido = self.connection.execute("SELECT quantidade_atual FROM lotes WHERE numero_lote = 'VENCIDO'").fetchone()[0]
        self.assertEqual(vencido, 10)

    def test_fefo_prioriza_validade_mais_proxima(self):
        self.entrada("L-2027", 10, "2027-12-31")
        self.entrada("L-2026", 20, "2026-10-20")
        alocacoes = registrar_saida_fefo(self.connection, self.produto_id, 10, 1)
        self.assertEqual([(item["numero_lote"], item["quantidade"]) for item in alocacoes], [("L-2026", 10.0)])

    def test_saida_pode_ser_dividida_entre_dois_lotes(self):
        self.entrada("L-2026", 3, "2026-10-20")
        self.entrada("L-2027", 5, "2027-12-31")
        alocacoes = registrar_saida_fefo(self.connection, self.produto_id, 6, 1)
        self.assertEqual([(item["numero_lote"], item["quantidade"]) for item in alocacoes], [("L-2026", 3.0), ("L-2027", 3.0)])
        self.assertEqual(self.saldo(), 2)

    def test_baixa_da_consulta_cria_item_e_movimentacao_vinculada(self):
        self.entrada("L-001", 5, "2027-12-31")
        itens = registrar_uso_consulta(self.connection, 1, self.produto_id, 2, 1)
        item = self.connection.execute("SELECT consulta_id, produto_id, lote_id, quantidade, movimentacao_id FROM itens_consulta").fetchone()
        movement = self.connection.execute("SELECT tipo, consulta_id FROM movimentacoes_estoque WHERE tipo = 'Saída'").fetchone()
        self.assertEqual(len(itens), 1)
        self.assertEqual((item["consulta_id"], item["produto_id"], item["quantidade"]), (1, self.produto_id, 2))
        self.assertEqual((movement["tipo"], movement["consulta_id"]), ("Saída", 1))

    def test_estorno_retorna_saldo_e_nao_pode_ser_repetido(self):
        self.entrada("L-001", 5, "2027-12-31")
        saida = registrar_saida_fefo(self.connection, self.produto_id, 2, 1)[0]["movimentacao_id"]
        registrar_estorno(self.connection, saida, 1)
        self.assertEqual(self.saldo(), 5)
        with self.assertRaises(Exception):
            registrar_estorno(self.connection, saida, 1)

    def test_estorno_de_ajuste_de_aumento_reverte_a_variacao(self):
        lote_id, _ = self.entrada("L-001", 5, "2027-12-31")
        from estoque.services import registrar_ajuste

        ajuste = registrar_ajuste(self.connection, lote_id, 8, 1, "Conferência")
        self.assertEqual(self.saldo(), 8)
        registrar_estorno(self.connection, ajuste, 1)
        self.assertEqual(self.saldo(), 5)

    def test_consumo_medio_eh_calculado_com_historico(self):
        self.entrada("L-001", 10, "2027-12-31")
        registrar_saida_fefo(self.connection, self.produto_id, 2, 1)
        consumo = consumo_por_produto(self.connection, self.produto_id, dias=30)
        self.assertEqual(consumo["quantidade"], 2)
        self.assertGreater(consumo["medio_diario"], 0)


if __name__ == "__main__":
    unittest.main()
