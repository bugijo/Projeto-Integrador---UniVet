"""Regressões dos relatos acadêmicos de outubro, sempre em SQLite descartável."""
import unittest
from html.parser import HTMLParser

import app as web
import test_app as fixtures


class AcademicRegressions(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.UniVetAppTests()
        self.fixture.setUp()
        self.client = self.fixture.client
        self.fixture._login('admin', '123456')

    def tearDown(self):
        self.fixture.tearDown()

    def test_manual_exit_commits_once_and_redirect_renders_totals(self):
        with self.fixture._conexao() as conn:
            product = conn.execute('SELECT produto_id FROM lotes WHERE quantidade_atual>5 AND validade>\'2090-01-01\' LIMIT 1').fetchone()
            if product is None:
                product = conn.execute('SELECT produto_id FROM lotes LIMIT 1').fetchone()
                conn.execute("UPDATE lotes SET validade='2099-12-31', quantidade_atual=20 WHERE produto_id=?", (product[0],))
            product_id = product[0]
            before = conn.execute('SELECT SUM(quantidade_atual) FROM lotes WHERE produto_id=?', (product_id,)).fetchone()[0]
        response = self.client.post('/estoque/saidas', data={'produto_id':product_id, 'quantidade':'1', 'motivo':'Uso interno fictício', 'valor_unitario_praticado':'5'}, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn('5,00', response.get_data(as_text=True))
        self.assertEqual(self.client.get('/estoque/movimentacoes').status_code, 200)
        with self.fixture._conexao() as conn:
            self.assertEqual(conn.execute('SELECT SUM(quantidade_atual) FROM lotes WHERE produto_id=?', (product_id,)).fetchone()[0], before-1)
            from estoque.services import listar_movimentacoes
            movement = next(row for row in listar_movimentacoes(conn, {'produto_id': product_id}) if row['motivo'] == 'Uso interno fictício')
            self.assertEqual(movement['valor_total'], 5)

    def test_brazilian_money_values(self):
        for value, expected in [(0,'R$\u00a00,00'),(5,'R$\u00a05,00'),(99.9,'R$\u00a099,90'),(1000,'R$\u00a01.000,00'),(5354,'R$\u00a05.354,00'),(1234567.89,'R$\u00a01.234.567,89')]:
            with self.subTest(value=value):
                with web.app.app_context():
                    self.assertEqual(web.app.jinja_env.from_string('{{ value|moeda_br }}').render(value=value), expected)

    def test_styles_and_navigation_have_content_version_in_rendered_urls(self):
        from urllib.parse import urlsplit, parse_qs
        class Assets(HTMLParser):
            def __init__(self):
                super().__init__(); self.urls=[]
            def handle_starttag(self, tag, attrs):
                attrs=dict(attrs)
                value=attrs.get('href') if tag=='link' else attrs.get('src') if tag=='script' else None
                if value and value.startswith('/static/') and ('.css' in value or '.js' in value):
                    self.urls.append(value)
        parser=Assets()
        parser.feed(self.client.get('/pagina-inicial').get_data(as_text=True))
        self.assertEqual(len(parser.urls),3)
        for url in parser.urls:
            with self.subTest(url=url):
                version=parse_qs(urlsplit(url).query).get('v',[''])[0]
                self.assertRegex(version,r'^[0-9a-f]{12}$')
                self.assertEqual(self.client.get(url).status_code,200)

    def test_product_exit_preselected(self):
        page = self.client.get('/estoque/saidas?produto_id=1').get_data(as_text=True)
        from html.parser import HTMLParser
        class Options(HTMLParser):
            selected = []
            def handle_starttag(self, tag, attrs):
                values = dict(attrs)
                if tag == 'option' and 'selected' in values:
                    self.selected.append(values.get('value'))
        parser = Options()
        parser.feed(page)
        self.assertIn('1', parser.selected)

    def test_replayed_exit_form_does_not_deduct_twice(self):
        class Hidden(HTMLParser):
            value = ''
            def handle_starttag(self, tag, attrs):
                attrs = dict(attrs)
                if tag == 'input' and attrs.get('name') == 'operacao_token':
                    self.value = attrs['value']
        parser = Hidden()
        parser.feed(self.client.get('/estoque/saidas').get_data(as_text=True))
        self.assertTrue(parser.value, 'Cada formulário deve ter uma chave de operação independente do CSRF')
        with self.fixture._conexao() as conn:
            conn.execute("UPDATE lotes SET quantidade_atual=20,validade='2099-12-31' WHERE produto_id=1")
        data = {'produto_id':'1','quantidade':'1','motivo':'Descarte fictício','valor_unitario_praticado':'0','operacao_token':parser.value}
        self.assertEqual(self.client.post('/estoque/saidas',data=data).status_code,302)
        with self.fixture._conexao() as conn:
            before = conn.execute('SELECT SUM(quantidade_atual) FROM lotes WHERE produto_id=1').fetchone()[0]
        self.assertEqual(self.client.post('/estoque/saidas',data=data).status_code,302)
        with self.fixture._conexao() as conn:
            self.assertEqual(conn.execute('SELECT SUM(quantidade_atual) FROM lotes WHERE produto_id=1').fetchone()[0],before)

    def test_movement_null_prices_old_dates_and_inactive_product(self):
        with self.fixture._conexao() as conn:
            conn.execute('UPDATE produtos SET ativo=0 WHERE id=1')
            conn.execute("UPDATE movimentacoes_estoque SET valor_unitario_praticado=NULL,usuario_id=NULL,criado_em='registro legado' WHERE produto_id=1")
        for query in ['', '?produto_id=1', '?tipo=Entrada', '?pagina=2&por_pagina=1', '?tipo=Estorno', '?data_inicio=2099-01-01']:
            with self.subTest(query=query):
                self.assertEqual(self.client.get('/estoque/movimentacoes'+query).status_code,200)

    def test_movement_order_accepts_both_legacy_timestamp_separators(self):
        from estoque.services import listar_movimentacoes
        with self.fixture._conexao() as conn:
            ids=[row[0] for row in conn.execute('SELECT id FROM movimentacoes_estoque ORDER BY id LIMIT 2')]
            conn.execute("UPDATE movimentacoes_estoque SET criado_em='2000-01-01 00:00:00'")
            conn.execute("UPDATE movimentacoes_estoque SET criado_em='2099-01-01T13:29' WHERE id=?",(ids[0],))
            conn.execute("UPDATE movimentacoes_estoque SET criado_em='2099-01-01 13:43:00' WHERE id=?",(ids[1],))
            for filters in ({},{'paginado':True,'por_pagina':1}):
                result=listar_movimentacoes(conn,filters)
                rows=result['itens'] if filters else result
                self.assertEqual(rows[0]['id'],ids[1])

    def test_empty_movements_render(self):
        with self.fixture._conexao() as conn:
            conn.execute('DELETE FROM itens_consulta')
            conn.execute('DELETE FROM movimentacoes_estoque')
        response=self.client.get('/estoque/movimentacoes')
        self.assertEqual(response.status_code,200)
        self.assertIn('Nenhuma movimentação',response.get_data(as_text=True))

    def test_names_are_utf8_plain_text_and_not_changed(self):
        names=['Luna','Thor','Mel','Bob','São Bento','Joãozinho','Coração']
        with self.fixture._conexao() as conn:
            ids=[row[0] for row in conn.execute('SELECT id FROM pets ORDER BY id LIMIT 7')]
            for identifier,name in zip(ids,names):
                conn.execute('UPDATE pets SET nome=? WHERE id=?',(name,identifier))
        response=self.client.get('/pets').get_data(as_text=True)
        for name in names:
            self.assertIn('<td>'+name+'</td>',response)

    def test_consultation_replay_is_once_and_linked_to_pet(self):
        with self.fixture._conexao() as conn:
            conn.execute("UPDATE lotes SET quantidade_atual=20,validade='2099-12-31' WHERE produto_id IN (1,2)")
            consultation,pet=conn.execute('SELECT id,pet_id FROM consultas LIMIT 1').fetchone()
        with web.app.test_request_context():
            from flask import session
            session['usuario_id']=1
            token=web.stock_operation_token('consulta:'+str(consultation))
        data={'produto_id':'1','quantidade':'2','motivo':'Material fictício','valor_unitario_praticado':'0','operacao_token':token}
        path=f'/consultas/{consultation}/produtos'
        self.assertEqual(self.client.post(path,data=data,follow_redirects=True).status_code,200)
        with self.fixture._conexao() as conn:
            count=conn.execute('SELECT COUNT(*) FROM itens_consulta WHERE consulta_id=?',(consultation,)).fetchone()[0]
        self.assertEqual(self.client.post(path,data=data,follow_redirects=True).status_code,200)
        with self.fixture._conexao() as conn:
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM itens_consulta WHERE consulta_id=?',(consultation,)).fetchone()[0],count)
            self.assertEqual(conn.execute('SELECT c.pet_id FROM itens_consulta i JOIN consultas c ON c.id=i.consulta_id WHERE i.consulta_id=?',(consultation,)).fetchone()[0],pet)
        second={**data,'produto_id':'2'}
        second.pop('operacao_token')
        self.assertEqual(self.client.post(path,data=second,follow_redirects=True).status_code,200)

    def test_failed_exit_rolls_back_operation_and_can_retry(self):
        with self.fixture._conexao() as conn:
            conn.execute("UPDATE lotes SET quantidade_atual=2,validade='2099-12-31' WHERE produto_id=1")
            before=conn.execute('SELECT SUM(quantidade_atual) FROM lotes WHERE produto_id=1').fetchone()[0]
        with web.app.test_request_context():
            from flask import session
            session['usuario_id']=1
            token=web.stock_operation_token('saida')
        data={'produto_id':'1','quantidade':'9999','motivo':'Teste de rollback','valor_unitario_praticado':'0','operacao_token':token}
        self.assertEqual(self.client.post('/estoque/saidas',data=data).status_code,200)
        with self.fixture._conexao() as conn:
            self.assertEqual(conn.execute('SELECT SUM(quantidade_atual) FROM lotes WHERE produto_id=1').fetchone()[0],before)
        data['quantidade']='1'
        self.assertEqual(self.client.post('/estoque/saidas',data=data).status_code,302)

    def test_invalid_operation_token_is_rejected(self):
        self.assertEqual(self.client.post('/estoque/saidas',data={'produto_id':'1','quantidade':'1','operacao_token':'invalid'}).status_code,400)

    def test_simultaneous_replay_is_serialized(self):
        from concurrent.futures import ThreadPoolExecutor
        import threading
        from estoque.services import registrar_saida_fefo
        with self.fixture._conexao() as conn:
            conn.execute("UPDATE lotes SET quantidade_atual=20,validade='2099-12-31' WHERE produto_id=1")
            before=conn.execute('SELECT SUM(quantidade_atual) FROM lotes WHERE produto_id=1').fetchone()[0]
        barrier=threading.Barrier(2)
        def submit(_):
            conn=self.fixture._conexao()
            try:
                barrier.wait(timeout=10)
                return registrar_saida_fefo(conn,1,1,1,'Concorrência fictícia',operacao_id='mesma-operacao-concorrente')
            finally:
                conn.close()
        with ThreadPoolExecutor(max_workers=2) as executor:
            results=list(executor.map(submit,range(2)))
        self.assertEqual(sum(bool(result) for result in results),1)
        with self.fixture._conexao() as conn:
            self.assertEqual(conn.execute('SELECT SUM(quantidade_atual) FROM lotes WHERE produto_id=1').fetchone()[0],before-1)

    def test_admin_can_create_professional_and_service_for_demo(self):
        for path,data,table in [('/veterinarios/novo',{'nome':'Veterinário Fictício QA'},'veterinarios'),('/servicos/novo',{'nome':'Serviço Fictício QA','duracao_minutos':'40'},'servicos')]:
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code,200)
                self.assertEqual(self.client.post(path,data=data).status_code,302)
                with self.fixture._conexao() as conn:
                    row=conn.execute(f'SELECT id FROM {table} WHERE nome=?',(data['nome'],)).fetchone()
                    self.assertIsNotNone(row)
                    self.assertEqual(conn.execute('SELECT COUNT(*) FROM historico_alteracoes WHERE entidade=? AND registro_id=?',(table,row[0])).fetchone()[0],1)
                self.assertEqual(self.client.post(path,data=data).status_code,200)
        self.client.post('/logout')
        self.fixture._login('vet.demo','Fer123')
        self.assertEqual(self.client.post('/veterinarios/novo',data={'nome':'Bloqueado QA'}).status_code,403)
        self.assertEqual(self.client.post('/servicos/novo',data={'nome':'Bloqueado QA','duracao_minutos':'20'}).status_code,403)

    def test_full_academic_crud_stock_consultation_and_exports(self):
        def post(path, data):
            response=self.client.post(path,data=data)
            self.assertEqual(response.status_code,302,(path,response.get_data(as_text=True)[:120]))
            self.assertEqual(self.client.get(response.location).status_code,200,path)
        def identifier(table,name):
            with self.fixture._conexao() as conn:
                row=conn.execute(f'SELECT id FROM {table} WHERE nome=?',(name,)).fetchone()
                self.assertIsNotNone(row,(table,name))
                return row[0]
        tutor={'nome':'Tutor exclusivamente fictício QA','telefone':'(11) 00000-0000','cpf':'93541134780','endereco':'Endereço fictício para teste'}
        post('/tutores/novo',tutor)
        tutor_id=identifier('tutores',tutor['nome'])
        post(f'/tutores/{tutor_id}/editar',{**tutor,'endereco':'Endereço fictício editado'})
        self.assertIn(tutor['nome'],self.client.get('/tutores?busca=fictício').get_data(as_text=True))
        self.assertEqual(self.client.post('/tutores/novo',data={**tutor,'cpf':'000'}).status_code,200)
        with self.fixture._conexao() as conn:
            species=conn.execute('SELECT id FROM especies LIMIT 1').fetchone()[0]
            breed=conn.execute('SELECT id FROM racas WHERE especie_id=? LIMIT 1',(species,)).fetchone()[0]
        pet={'nome':'Coração QA','especie_id':species,'raca_id':breed,'tutor_id':tutor_id,'idade':'2 anos','historico':'Somente simulação'}
        post('/pets/novo',pet)
        pet_id=identifier('pets',pet['nome'])
        post(f'/pets/{pet_id}/editar',{**pet,'idade':'3 anos'})
        post('/veterinarios/novo',{'nome':'Profissional fictício fluxo QA'})
        vet=identifier('veterinarios','Profissional fictício fluxo QA')
        post(f'/veterinarios/{vet}/editar',{'nome':'Profissional fictício fluxo QA'})
        post('/servicos/novo',{'nome':'Serviço fictício fluxo QA','duracao_minutos':'20'})
        service=identifier('servicos','Serviço fictício fluxo QA')
        post(f'/servicos/{service}/editar',{'nome':'Serviço fictício fluxo QA','duracao_minutos':'40'})
        post('/estoque/categorias',{'nome':'Categoria fictícia fluxo QA','descricao':'Teste'})
        category=identifier('categorias','Categoria fictícia fluxo QA')
        post('/estoque/fornecedores',{'nome':'Fornecedor fictício fluxo QA'})
        supplier=identifier('fornecedores','Fornecedor fictício fluxo QA')
        product={'nome':'=Produto fictício ç QA','codigo':'QA-FLUXO-001','tipo':'Material','categoria_id':category,'unidade_medida':'ml','estoque_minimo':'3','margem_lucro_percentual':'30'}
        post('/estoque/produtos/novo',product)
        product_id=identifier('produtos',product['nome'])
        for index,qty in enumerate([3,5,7],start=1):
            post('/estoque/lotes/entrada',{'produto_id':product_id,'fornecedor_id':supplier,'numero_lote':f'QA-{index}','quantidade':str(qty),'validade':f'2099-0{index}-01','valor_compra_unitario':'10','motivo':'Entrada fictícia'})
        post('/estoque/saidas',{'produto_id':product_id,'quantidade':'4','valor_unitario_praticado':'0','motivo':'Uso interno fictício'})
        with self.fixture._conexao() as conn:
            self.assertEqual([r[0] for r in conn.execute('SELECT quantidade_atual FROM lotes WHERE produto_id=? ORDER BY validade',(product_id,))],[0,4,7])
            movement=conn.execute("SELECT id FROM movimentacoes_estoque WHERE produto_id=? AND tipo='Saída' ORDER BY id DESC LIMIT 1",(product_id,)).fetchone()[0]
        post(f'/estoque/movimentacoes/{movement}/estornar',{'motivo':'Estorno fictício'})
        consultation={'data_hora':'2099-01-05T15:00','pet_id':pet_id,'servico_id':service,'veterinario_id':vet,'tipo_atendimento':'Presencial','confirmacao_status':'Confirmada','status':'Agendada'}
        post('/consultas/nova',consultation)
        with self.fixture._conexao() as conn:
            consult=conn.execute('SELECT id FROM consultas WHERE pet_id=?',(pet_id,)).fetchone()[0]
        post(f'/consultas/{consult}/produtos',{'produto_id':product_id,'quantidade':'2','motivo':'Material fictício','valor_unitario_praticado':'0'})
        post(f'/consultas/{consult}/editar',{**consultation,'status':'Concluida'})
        self.assertEqual(self.client.get(f'/historico/consultas/{consult}').status_code,200)
        with self.fixture._conexao() as conn:
            self.assertEqual(conn.execute('SELECT pet_id FROM consultas WHERE id=?',(consult,)).fetchone()[0],pet_id)
            lot=conn.execute('SELECT id,quantidade_atual FROM lotes WHERE produto_id=? ORDER BY id DESC',(product_id,)).fetchone()
        post(f'/estoque/lotes/{lot[0]}/ajuste',{'nova_quantidade':'6','motivo':'Ajuste fictício'})
        for path in ['/estoque/relatorios','/estoque/relatorios?dias=7&produto_id=999999','/api/estoque/produtos?pagina=1&por_pagina=1','/api/estoque/movimentacoes?pagina=999','/api/estoque/resumo']:
            self.assertEqual(self.client.get(path).status_code,200,path)
        csv=self.client.get('/estoque/exportar/posicao.csv')
        self.assertEqual(csv.status_code,200)
        self.assertIn('fictício ç QA',csv.get_data(as_text=True))
        self.assertIn("'=Produto",csv.get_data(as_text=True))
        post('/logout',{})
        self.assertEqual(self.client.get('/tutores').status_code,302)
        self.assertEqual(self.client.get('/api/estoque/resumo').status_code,401)
