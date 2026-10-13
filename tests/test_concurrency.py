"""Regressões em SQLite descartável, sem importar app/init_db ou dados reais."""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sqlite3
import tempfile
import threading
import unittest

from estoque.schema import criar_tabelas_estoque
from estoque import services as estoque


class SynchronizedConnection(sqlite3.Connection):
    barrier = None

    def execute(self, sql, parameters=()):
        # Todos chegam ao lock antes de qualquer escritor prosseguir. Na versão
        # antiga isto força as leituras vulneráveis a observarem o mesmo saldo.
        if sql == "BEGIN IMMEDIATE" and self.barrier is not None:
            self.barrier.wait(timeout=10)
        return super().execute(sql, parameters)


class EstoqueConcurrencyTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="univet-concurrency-")
        self.addCleanup(temporary.cleanup)
        self.path = Path(temporary.name) / "test.sqlite"
        self.connection = self.connect()
        self.addCleanup(self.connection.close)
        self.connection.executescript("""
            CREATE TABLE usuarios (id INTEGER PRIMARY KEY, nome TEXT);
            CREATE TABLE consultas (id INTEGER PRIMARY KEY);
            INSERT INTO usuarios VALUES (1, 'Teste');
            INSERT INTO consultas VALUES (1);
        """)
        criar_tabelas_estoque(self.connection)
        self.connection.commit()

    def connect(self):
        connection = sqlite3.connect(self.path, timeout=10, factory=SynchronizedConnection)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def product(self):
        product = self.connection.execute(
            "INSERT INTO produtos (nome, tipo) VALUES ('Teste', 'Material')"
        ).lastrowid
        self.connection.commit()
        return product

    def entry(self, product, name, quantity, expiry=None):
        return estoque.registrar_entrada(
            self.connection, product, None, name, quantity, expiry, 10, 1
        )

    def race(self, count, operation):
        barrier = threading.Barrier(count)

        def worker(index):
            connection = self.connect()
            connection.barrier = barrier
            try:
                try:
                    result = operation(connection, index)
                except estoque.EstoqueError as error:
                    result = error
                self.assertFalse(connection.in_transaction)
                return result
            finally:
                connection.close()

        with ThreadPoolExecutor(max_workers=count) as executor:
            futures = [executor.submit(worker, index) for index in range(count)]
            return [future.result(timeout=30) for future in futures]

    def assert_ledger(self, product):
        for lot in self.connection.execute("SELECT * FROM lotes WHERE produto_id = ?", (product,)):
            balance = 0
            for movement in self.connection.execute(
                "SELECT quantidade_variacao FROM movimentacoes_estoque WHERE lote_id = ? ORDER BY id",
                (lot["id"],),
            ):
                balance += movement[0]
                self.assertGreaterEqual(balance, 0)
            self.assertAlmostEqual(balance, lot["quantidade_atual"])

    def test_saidas_fefo_e_consulta_com_2_5_10_conexoes(self):
        for count in (2, 5, 10):
            for consultation in (False, True):
                with self.subTest(connections=count, consultation=consultation):
                    product = self.product()
                    # Criação fora de ordem, vencido, inativo e sem validade.
                    late, _ = self.entry(product, "tardio", count, "2099-12-31")
                    early, _ = self.entry(product, "cedo", count - 1, "2099-01-01")
                    undated, _ = self.entry(product, "sem-validade", 1)
                    expired, _ = self.entry(product, "vencido", 10, "2000-01-01")
                    inactive, _ = self.entry(product, "inativo", 10, "2098-01-01")
                    self.connection.execute("UPDATE lotes SET ativo = 0 WHERE id = ?", (inactive,))
                    self.connection.commit()

                    def withdraw(connection, _):
                        if consultation:
                            return estoque.registrar_uso_consulta(connection, 1, product, 2, 1)
                        return estoque.registrar_saida_fefo(connection, product, 2, 1)

                    results = self.race(count, withdraw)
                    self.assertTrue(all(isinstance(result, list) for result in results))
                    movements = self.connection.execute(
                        "SELECT lote_id, quantidade FROM movimentacoes_estoque WHERE produto_id = ? AND tipo = 'Saída' ORDER BY id",
                        (product,),
                    ).fetchall()
                    self.assertEqual(sum(row["quantidade"] for row in movements), 2 * count)
                    ids = [row["lote_id"] for row in movements]
                    self.assertEqual(ids, sorted(ids, key={early: 0, late: 1, undated: 2}.__getitem__))
                    self.assertEqual(ids[-1], undated)
                    self.assertNotIn(expired, ids)
                    self.assertNotIn(inactive, ids)
                    if consultation:
                        items = self.connection.execute(
                            "SELECT COUNT(*) FROM itens_consulta WHERE produto_id = ?", (product,)
                        ).fetchone()[0]
                        self.assertEqual(items, len(movements))
                    self.assert_ledger(product)

    def test_disputa_saldo_insuficiente_rollback(self):
        for count in (2, 5, 10):
            with self.subTest(connections=count):
                product = self.product()
                lot, _ = self.entry(product, "unico", count - 1)
                results = self.race(count, lambda connection, _: estoque.registrar_saida_fefo(connection, product, 1, 1))
                self.assertEqual(sum(isinstance(result, estoque.EstoqueInsuficiente) for result in results), 1)
                self.assertEqual(sum(isinstance(result, list) for result in results), count - 1)
                self.assertEqual(self.connection.execute("SELECT quantidade_atual FROM lotes WHERE id = ?", (lot,)).fetchone()[0], 0)
                self.assert_ledger(product)

    def test_estorno_concorrente_unico(self):
        for count in (2, 5, 10):
            with self.subTest(connections=count):
                product = self.product()
                self.entry(product, "unico", 10)
                original = estoque.registrar_saida_fefo(self.connection, product, 3, 1)[0]["movimentacao_id"]
                results = self.race(count, lambda connection, _: estoque.registrar_estorno(connection, original, 1))
                self.assertEqual(sum(isinstance(result, int) for result in results), 1)
                errors = [result for result in results if isinstance(result, estoque.EstoqueError)]
                self.assertEqual(len(errors), count - 1)
                self.assertTrue(all("já possui" in str(error) for error in errors))
                self.assertEqual(self.connection.execute(
                    "SELECT COUNT(*) FROM movimentacoes_estoque WHERE movimentacao_origem_id = ?", (original,)
                ).fetchone()[0], 1)
                self.assert_ledger(product)

    def test_ajustes_concorrentes_preservam_historico(self):
        for count in (2, 5, 10):
            for same_target in (False, True):
                with self.subTest(connections=count, same_target=same_target):
                    product = self.product()
                    lot, _ = self.entry(product, "unico", 100)
                    results = self.race(count, lambda connection, index: estoque.registrar_ajuste(
                        connection, lot, 50 if same_target else 50 + index, 1, "Contagem"
                    ))
                    self.assertEqual(sum(isinstance(result, int) for result in results), 1 if same_target else count)
                    self.assert_ledger(product)

    def test_schema_impede_estorno_duplicado_direto(self):
        product = self.product()
        self.entry(product, "unico", 10)
        original = estoque.registrar_saida_fefo(self.connection, product, 1, 1)[0]["movimentacao_id"]
        reversal = estoque.registrar_estorno(self.connection, original, 1)
        with self.assertRaises(sqlite3.IntegrityError):
            self.connection.execute("""
                INSERT INTO movimentacoes_estoque (produto_id, lote_id, tipo, quantidade, motivo, movimentacao_origem_id)
                SELECT produto_id, lote_id, tipo, quantidade, motivo, movimentacao_origem_id
                FROM movimentacoes_estoque WHERE id = ?
            """, (reversal,))
        self.connection.rollback()
        criar_tabelas_estoque(self.connection)
        self.connection.commit()
        self.assert_ledger(product)

    def test_ajuste_disputa_com_saida(self):
        product = self.product()
        lot, _ = self.entry(product, "unico", 100)

        def operation(connection, index):
            if index == 0:
                return estoque.registrar_ajuste(connection, lot, 50, 1, "Contagem")
            return estoque.registrar_saida_fefo(connection, product, 10, 1)

        results = self.race(2, operation)
        self.assertTrue(all(isinstance(result, (int, list)) for result in results))
        self.assert_ledger(product)

    def test_limites_e_estorno_acima_do_maximo(self):
        product = self.product()
        lot, _ = self.entry(product, "maximo", estoque.MAX_QUANTIDADE)
        original = estoque.registrar_saida_fefo(
            self.connection, product, 1, 1, valor_unitario_praticado=estoque.MAX_VALOR
        )[0]["movimentacao_id"]
        estoque.registrar_ajuste(self.connection, lot, estoque.MAX_QUANTIDADE, 1, "Contagem")
        with self.assertRaises(estoque.EstoqueError):
            estoque.registrar_estorno(self.connection, original, 1)
        self.assertFalse(self.connection.in_transaction)
        self.assertEqual(self.connection.execute(
            "SELECT COUNT(*) FROM movimentacoes_estoque WHERE tipo = 'Estorno'"
        ).fetchone()[0], 0)
        self.assert_ledger(product)
        estoque.registrar_ajuste(self.connection, lot, 0, 1, "Zerar")
        self.assert_ledger(product)

    def test_margem_e_preco_calculado_invalidos(self):
        product = self.product()
        for margin, price in ((float("inf"), 1), (-1, 1), (estoque.MAX_MARGEM + 1, 1), (30, estoque.MAX_VALOR)):
            with self.subTest(margin=margin, price=price):
                self.connection.execute("UPDATE produtos SET margem_lucro_percentual = ? WHERE id = ?", (margin, product))
                self.connection.commit()
                with self.assertRaises(estoque.EstoqueError):
                    estoque.registrar_entrada(self.connection, product, None, "invalido", 1, None, price, 1)
                self.assertEqual(self.connection.execute("SELECT COUNT(*) FROM lotes").fetchone()[0], 0)

    def test_preco_sugerido_invalido_reverte_saida_multilote(self):
        product = self.product()
        self.entry(product, "primeiro", 1, "2099-01-01")
        second, _ = self.entry(product, "segundo", 1, "2099-12-31")
        self.connection.execute("UPDATE lotes SET valor_venda_sugerido_unitario = ? WHERE id = ?", (float("inf"), second))
        self.connection.commit()
        for consultation in (False, True):
            with self.subTest(consultation=consultation):
                with self.assertRaises(estoque.EstoqueError):
                    if consultation:
                        estoque.registrar_uso_consulta(self.connection, 1, product, 2, 1)
                    else:
                        estoque.registrar_saida_fefo(self.connection, product, 2, 1)
                self.assertEqual(self.connection.execute("SELECT COUNT(*) FROM movimentacoes_estoque").fetchone()[0], 2)
                self.assertEqual(self.connection.execute("SELECT COUNT(*) FROM itens_consulta").fetchone()[0], 0)
                self.assert_ledger(product)

    def test_numeros_invalidos_nao_alteram_estoque(self):
        product = self.product()
        lot, _ = self.entry(product, "unico", 10)
        invalid = (float("nan"), float("inf"), float("-inf"), "NaN", "1e309", -1, 1e10, 10 ** 1000)
        for value in invalid:
            operations = (
                lambda: estoque.registrar_entrada(self.connection, product, None, "invalido", value, None, 1, 1),
                lambda: estoque.registrar_entrada(self.connection, product, None, "invalido", 1, None, value, 1),
                lambda: estoque.registrar_saida_fefo(self.connection, product, value, 1),
                lambda: estoque.registrar_uso_consulta(self.connection, 1, product, value, 1),
                lambda: estoque.registrar_ajuste(self.connection, lot, value, 1, "Teste"),
                lambda: estoque.registrar_saida_fefo(self.connection, product, 1, 1, valor_unitario_praticado=value),
                lambda: estoque.registrar_uso_consulta(self.connection, 1, product, 1, 1, valor_unitario_praticado=value),
            )
            for index, operation in enumerate(operations):
                with self.subTest(value=str(value)[:30], operation=index):
                    with self.assertRaises(estoque.EstoqueError):
                        operation()
                    self.assertFalse(self.connection.in_transaction)
                    self.assertEqual(self.connection.execute("SELECT COUNT(*) FROM movimentacoes_estoque").fetchone()[0], 1)
                    self.assertEqual(self.connection.execute("SELECT COUNT(*) FROM itens_consulta").fetchone()[0], 0)
                    self.assert_ledger(product)


if __name__ == "__main__":
    unittest.main()
