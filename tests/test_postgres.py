"""Executar com UNIVET_TEST_POSTGRES=1; Docker cria bancos próprios descartáveis."""
import os
import unittest
from pathlib import Path
import app as web
import init_db
from database import connect,close_pools
from pg_support import LocalPostgres
from support import FormClient
import test_app as legacy_http
import test_estoque as legacy_stock
import test_concurrency as legacy_races
from estoque import services as stock
from migrate import migrate
import psycopg


@unittest.skipUnless(os.environ.get('UNIVET_TEST_POSTGRES')=='1','PostgreSQL: ativar UNIVET_TEST_POSTGRES=1 (Docker isolado)')
class PostgresHTTPTests(legacy_http.UniVetAppTests):
    @classmethod
    def setUpClass(cls):
        cls.server=LocalPostgres().__enter__()
        cls.addClassCleanup(cls.server.stop)

    def setUp(self):
        self.db_path=self.server.database()
        self.database_original_app=web.DATABASE
        self.database_original_init=init_db.DATABASE
        web.DATABASE=init_db.DATABASE=self.db_path
        init_db.init_db(seed_demo=True)
        web.limpar_caches_referencia()
        web.app.config.update(TESTING=True)
        self.client=FormClient(web.app,web.app.response_class)

    def tearDown(self):
        web.DATABASE=self.database_original_app
        init_db.DATABASE=self.database_original_init
        web.limpar_caches_referencia()
        close_pools()

    def _conexao(self):
        return connect(self.db_path)


class CoreFixture:
    @classmethod
    def setUpClass(cls):
        cls.server=LocalPostgres().__enter__()
        cls.addClassCleanup(cls.server.stop)

    def core(self):
        self.path=self.server.database()
        migrate(self.path,'development')
        self.connection=connect(self.path,pool_size=16)
        self.addCleanup(close_pools)
        self.addCleanup(self.connection.close)
        self.connection.execute("INSERT INTO usuarios(id,login,nome,perfil,senha_hash) VALUES (1,'fictitious','Teste','admin','not-a-login-hash')")
        self.connection.execute("INSERT INTO tutores(id,nome,telefone) VALUES (1,'Tutor fictício','000')")
        self.connection.execute("INSERT INTO pets(id,nome,especie,tutor_id) VALUES (1,'Pet fictício','Cão',1)")
        self.connection.execute("INSERT INTO consultas(id,pet_id,data_hora,status) VALUES (1,1,'2099-01-01T10:00','Agendada')")
        self.connection.commit()


@unittest.skipUnless(os.environ.get('UNIVET_TEST_POSTGRES')=='1','PostgreSQL isolado opt-in')
class PostgresStockTests(CoreFixture,legacy_stock.EstoqueServicesTests):
    def setUp(self):
        self.core()
        self.categoria_id=self.connection.execute("INSERT INTO categorias(nome) VALUES ('Medicamentos')").lastrowid
        self.fornecedor_id=self.connection.execute("INSERT INTO fornecedores(nome) VALUES ('Fornecedor teste')").lastrowid
        self.produto_id=self.connection.execute("INSERT INTO produtos(nome,codigo,tipo,categoria_id,unidade_medida,estoque_minimo) VALUES ('Produto teste','TEST-001','Medicamento',?,'unidade',5)",(self.categoria_id,)).lastrowid
        self.connection.commit()

    def tearDown(self):
        pass  # addCleanup fecha conexão/pool; apenas banco do contêiner fictício.


class BarrierConnection:
    def __init__(self,target):
        self.connection=connect(target,pool_size=16)
        self.barrier=None

    def execute(self,sql,params=()):
        if sql=='SELECT pg_advisory_xact_lock(734120, 1)' and self.barrier:
            self.barrier.wait(timeout=15)
        return self.connection.execute(sql,params)

    def __getattr__(self,name):
        return getattr(self.connection,name)


@unittest.skipUnless(os.environ.get('UNIVET_TEST_POSTGRES')=='1','PostgreSQL isolado opt-in')
class PostgresConcurrencyTests(CoreFixture,legacy_races.EstoqueConcurrencyTests):
    def setUp(self):
        self.core()

    def connect(self):
        return BarrierConnection(self.path)

    def test_schema_impede_estorno_duplicado_direto(self):
        product=self.product()
        self.entry(product,'unico',10)
        original=stock.registrar_saida_fefo(self.connection,product,1,1)[0]['movimentacao_id']
        reversal=stock.registrar_estorno(self.connection,original,1)
        with self.assertRaises(psycopg.errors.UniqueViolation):
            self.connection.execute("INSERT INTO movimentacoes_estoque(produto_id,lote_id,tipo,quantidade,quantidade_variacao,motivo,movimentacao_origem_id) SELECT produto_id,lote_id,tipo,quantidade,quantidade_variacao,motivo,movimentacao_origem_id FROM movimentacoes_estoque WHERE id=?",(reversal,))
        self.connection.rollback()
        self.assert_ledger(product)

    def test_margem_e_preco_calculado_invalidos(self):
        product=self.product()
        for margin in ('Infinity',-1,stock.MAX_MARGEM+1):
            with self.assertRaises(psycopg.Error):
                self.connection.execute('UPDATE produtos SET margem_lucro_percentual=? WHERE id=?',(margin,product))
            self.connection.rollback()
        with self.assertRaises(stock.EstoqueError):
            stock.registrar_entrada(self.connection,product,None,'overflow',1,None,stock.MAX_VALOR,1)
        self.assertEqual(self.connection.execute('SELECT count(*) FROM lotes').fetchone()[0],0)

    def test_preco_sugerido_invalido_reverte_saida_multilote(self):
        product=self.product()
        self.entry(product,'primeiro',1,'2099-01-01')
        second,_=self.entry(product,'segundo',1,'2099-12-31')
        with self.assertRaises(psycopg.Error):
            self.connection.execute('UPDATE lotes SET valor_venda_sugerido_unitario=? WHERE id=?',('Infinity',second))
        self.connection.rollback()
        # Injetar erro entre parcelas sem violar/relaxar o schema mais forte.
        from unittest.mock import patch
        real=stock._valor_praticado
        for consultation in (False,True):
            calls=[]
            def fail_later(*args):
                calls.append(1)
                if len(calls)>=3:
                    raise stock.EstoqueError('Falha fictícia')
                return real(*args)
            with patch.object(stock,'_valor_praticado',side_effect=fail_later),self.assertRaises(stock.EstoqueError):
                if consultation:
                    stock.registrar_uso_consulta(self.connection,1,product,2,1)
                else:
                    stock.registrar_saida_fefo(self.connection,product,2,1)
            self.assertEqual(self.connection.execute('SELECT count(*) FROM movimentacoes_estoque').fetchone()[0],2)
            self.assert_ledger(product)
