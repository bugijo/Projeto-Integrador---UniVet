# Relatório Parcial — Evolução do UniVet com módulo integrado de estoque

**Projeto:** Projeto Integrador II  
**Sistema:** UniVet 2.0  
**Branch documentada:** `feature/integracao-propostas-estoque`  
**Data da consolidação:** 18/09/2026

> Este documento é um rascunho técnico-acadêmico baseado no estado verificável do repositório. Dados sem evidência documental estão marcados como `[PENDENTE DE PREENCHIMENTO PELO GRUPO]`.

## 1. Introdução

O UniVet é um sistema web de apoio à gestão de uma clínica veterinária, desenvolvido inicialmente no Projeto Integrador I. A primeira versão contemplou autenticação, cadastros de tutores, animais, veterinários e serviços, agenda de consultas e histórico clínico.

No Projeto Integrador II, o trabalho dá continuidade à aplicação existente. O principal avanço documentado é a criação e integração de um módulo de controle de estoque para produtos utilizados na rotina veterinária. A evolução foi realizada preservando a tecnologia e os módulos anteriores, com foco em produtos, lotes, validade, movimentações, alertas, consumo e integração com atendimentos.

O objetivo desta etapa é apresentar o estado parcial da solução, suas regras, sua organização técnica, os testes realizados e os pontos que ainda precisam ser validados com a comunidade externa.

## 2. Contextualização do problema

O Plano de Ação do PI II registra que a Clínica Veterinária Fernanda Calixto não dispunha, no diagnóstico anterior, de um controle informatizado integrado para medicamentos, vacinas e materiais. A ausência desse controle dificulta conhecer o saldo disponível, acompanhar fornecedores, registrar lotes e valores de compra, controlar prazos de validade e relacionar produtos utilizados aos atendimentos.

Esse cenário pode favorecer faltas imprevistas, perdas por vencimento e dificuldade de reconstruir as entradas e saídas. Por isso, a continuidade do UniVet foi direcionada à gestão de estoque integrada às consultas e ao histórico dos animais.

Não há, no repositório analisado, medição quantitativa de perdas ou de tempo operacional antes e depois da solução. Assim, não se deve afirmar que o sistema já reduziu perdas ou custos; ele foi desenvolvido com recursos que visam apoiar esses controles.

## 3. Problema de pesquisa

Como integrar o controle de estoque aos atendimentos veterinários, garantindo rastreabilidade dos produtos, prevenção de perdas por vencimento e atualização automática das quantidades disponíveis?

## 4. Objetivos

### 4.1 Objetivo geral

Evoluir o UniVet por meio da implementação de um módulo integrado de gerenciamento de estoque, preservando a aplicação clínica desenvolvida no Projeto Integrador I.

### 4.2 Objetivos específicos

- cadastrar produtos com nome, tipo, categoria, unidade, código e estoque mínimo;
- cadastrar categorias e fornecedores;
- registrar entradas por lote, com quantidade, validade e valor de compra;
- registrar saídas manuais e saídas vinculadas ao uso em consultas;
- controlar o saldo por lote e impedir estoque negativo;
- aplicar a regra FEFO nas saídas;
- bloquear a seleção de lotes vencidos para saídas normais;
- registrar ajustes e estornos de forma rastreável;
- relacionar produtos utilizados às consultas;
- realizar baixa automática quando um produto é utilizado em atendimento;
- disponibilizar alertas de estoque mínimo e validade;
- apresentar dashboard, relatórios, análise de consumo e sugestão transparente de reposição;
- oferecer filtros, paginação, exportação CSV e API autenticada;
- ampliar testes automatizados sem remover os testes do sistema anterior.

Os objetivos relativos a PWA, código de barras, PDF e previsão avançada de demanda não foram considerados objetivos realizados nesta versão.

## 5. Metodologia

O trabalho foi conduzido como continuidade do projeto anterior. O grupo utilizou o diagnóstico e a aplicação do PI I como ponto de partida, manteve a comunidade externa registrada no Plano de Ação e definiu o estoque como foco de evolução.

O processo documentado compreendeu:

1. revisão do código, README, banco, testes e configuração de deploy existentes;
2. levantamento dos fluxos clínicos e dos requisitos de estoque previstos no Plano de Ação;
3. comparação de propostas externas, repositórios e materiais compartilhados;
4. seleção de ideias compatíveis com a stack atual e com o semestre;
5. implementação incremental em branch própria;
6. criação de testes de regras, filtros, paginação, exportações e API;
7. execução da suíte completa e correção de falhas encontradas;
8. registro das decisões e da origem das ideias na documentação do repositório.

O contato de validação com a clínica está previsto nos documentos do projeto, mas o repositório não contém feedback final da médica veterinária sobre esta versão.

[PENDENTE DE COMPLEMENTO PELO GRUPO] Descrever datas, participantes, instrumentos e resultados das conversas realizadas durante o PI II.

## 6. Levantamento bibliográfico

Não foram encontradas, no repositório atual, referências bibliográficas acadêmicas suficientes para compor esta seção sem risco de invenção.

**[PENDENTE DE INSERÇÃO DAS REFERÊNCIAS BIBLIOGRÁFICAS]**

Temas que precisam ser pesquisados e referenciados pelo grupo:

- gestão e controle de estoque;
- rastreabilidade de produtos;
- FEFO — First Expire, First Out;
- sistemas web e arquitetura cliente-servidor;
- modelagem e integridade de banco de dados;
- testes de software;
- acessibilidade digital;
- gestão de clínicas veterinárias.

## 7. Tecnologias utilizadas

| Tecnologia | Papel no projeto |
|---|---|
| Python 3 | Linguagem principal do backend e dos scripts de inicialização |
| Flask | Framework web responsável pelas rotas, sessões e respostas |
| Jinja2 | Geração das páginas HTML a partir de templates |
| HTML5 | Estrutura das telas, formulários e tabelas |
| CSS3 | Identidade visual, layout, estados e responsividade |
| JavaScript | Interações de navegação, menu mobile, confirmação e comportamentos de tela |
| SQLite | Banco de dados usado no desenvolvimento e na demonstração local |
| Git | Controle de versões e organização das entregas |
| GitHub | Hospedagem do repositório e colaboração |
| GitHub Actions | Inicialização do banco, validação de sintaxe, testes e smoke test configurável |
| unittest | Testes automatizados da aplicação e do módulo de estoque |
| Render | Configuração de deploy gratuito em `render.yaml`; a persistência do SQLite em nuvem ainda exige validação |

Não foram adicionadas bibliotecas comerciais, APIs pagas ou serviços com cobrança por requisição.

## 8. Evolução da arquitetura

O UniVet permanece uma aplicação monolítica server-side em Flask. Essa decisão evita uma migração de arquitetura durante o semestre e preserva os módulos do PI I.

O núcleo original continua concentrado em `app.py`, que reúne rotas, preparação de contexto e parte das validações. Para o estoque, foi criada uma separação parcial:

- `estoque/schema.py`: criação incremental das tabelas, índices e colunas específicas do estoque;
- `estoque/services.py`: consultas, validações e regras de entrada, saída FEFO, uso em consulta, ajustes, estornos, consumo e reposição;
- `templates/estoque/`: páginas do módulo;
- `tests/test_estoque.py`: cenários específicos do domínio;
- `templates/_paginacao.html`: componente compartilhado de paginação.

Essa organização melhora a separação de responsabilidades sem exigir uma reescrita completa. A estrutura ainda pode evoluir, mas não foi feita uma grande refatoração apenas por preferência técnica.

## 9. Desenvolvimento da solução

### 9.1 Produtos

O cadastro de produtos contempla nome, código, tipo, categoria, unidade de medida, estoque mínimo, status ativo/inativo e margem de lucro. O custo e a validade são controlados nos lotes, pois podem variar a cada entrada. A tela de detalhes apresenta saldo, lotes, histórico, consumo e valor sugerido.

### 9.2 Categorias

Categorias podem ser cadastradas, editadas, pesquisadas e ativadas ou inativadas. Elas são usadas para organizar produtos e filtrar relatórios.

### 9.3 Fornecedores

Fornecedores possuem nome, documento, telefone, e-mail e endereço. A listagem oferece busca, filtro por status, paginação e ações administrativas.

### 9.4 Lotes

Cada entrada cria um lote relacionado a um produto. O lote guarda quantidade inicial, quantidade atual, validade, valor de compra unitário, valor de venda sugerido, fornecedor, data de entrada e status.

### 9.5 Entradas e saídas

A entrada valida lote, quantidade, validade e valor de compra. O valor sugerido é calculado a partir do custo e da margem definida para o produto.

As saídas manuais registram produto, quantidade, motivo e valor praticado. O saldo é reduzido por lote, respeitando a disponibilidade total e as regras de validade.

### 9.6 Ajustes e estornos

O ajuste permite registrar uma nova quantidade para um lote, exigindo motivo. A diferença é armazenada como movimentação. Saídas e ajustes podem ser estornados uma vez; o estorno cria um novo registro vinculado à movimentação original, em vez de apagar o histórico.

### 9.7 Controle FEFO

FEFO significa *First Expire, First Out*, ou “primeiro que vence, primeiro que sai”. Na saída, o sistema considera lotes ativos, com saldo positivo e não vencidos, ordenando primeiro a validade mais próxima. Se um lote não for suficiente, a quantidade pode ser dividida entre lotes, mantendo cada parcela rastreada.

### 9.8 Integração com consultas

O fluxo de uso clínico pode ser representado como:

```text
consulta → produto utilizado → lote selecionado por FEFO → baixa do saldo
         → item da consulta → movimentação registrada
```

O registro em `itens_consulta` guarda consulta, produto, lote, quantidade, movimentação e valores. O histórico clínico continua acessível junto aos atendimentos anteriores.

### 9.9 Alertas

O sistema calcula produtos abaixo do estoque mínimo e lotes vencidos ou próximos do vencimento. Esses estados aparecem no dashboard, nas listagens e nos relatórios. O limite padrão de alerta de validade é de 30 dias.

### 9.10 Dashboard

O dashboard de estoque apresenta produtos ativos, unidades, valor estimado pelo custo dos lotes ativos, produtos abaixo do mínimo, lotes vencendo, consumo recente, recomendações de reposição e movimentações recentes.

### 9.11 Relatórios

O relatório de consumo permite selecionar períodos de 7, 30, 90 ou 365 dias e filtrar produto ou categoria. Apresenta consumo total, produtos com uso, reposição recomendada, valor dos lotes, gráfico diário, ranking e detalhamento por produto.

### 9.12 Análise de consumo

O consumo é calculado a partir das movimentações de saída no período selecionado. O sistema também monta uma série diária para visualização e informa a média diária por produto.

### 9.13 Sugestão de reposição

A regra implementada é transparente: combina o estoque mínimo com uma cobertura de quatro semanas baseada na média diária de consumo. A sugestão não usa inteligência artificial nem promete previsão estatística.

### 9.14 Filtros, paginação e exportação

Foram integrados filtros de nome, código, tipo, categoria, situação e estoque crítico para produtos; produto, fornecedor, validade e vencimento para lotes; produto, tipo, usuário, consulta e período para movimentações; nome e status para fornecedores; e período, produto e categoria para relatórios.

Produtos, lotes, movimentações e fornecedores possuem paginação com página atual, total e navegação anterior/próxima. Foram criadas exportações CSV locais para movimentações, posição atual do estoque e consumo.

Uma API autenticada fornece resumo, produtos e movimentações em JSON. PDF foi avaliado, mas não incluído por não ser essencial e por exigir nova dependência sem benefício proporcional nesta etapa.

## 10. Interface e experiência do usuário

A interface foi modernizada com uma identidade visual compartilhada, sidebar, topbar, breadcrumbs, cards, tabelas, formulários, badges de estado, mensagens e componentes de ação. O dashboard e o estoque utilizam composição por blocos para destacar informações operacionais.

As telas do estoque receberam maior hierarquia para itens críticos, vencimentos, consumo, valores e histórico. Datas são apresentadas em formato brasileiro nas telas. Tabelas utilizam rolagem horizontal quando necessário, e formulários usam grids adaptáveis.

O layout possui comportamento para desktop, tablet e celular. Em telas menores, a sidebar pode ser aberta pelo menu hambúrguer; grids são reorganizados e tabelas permanecem acessíveis por rolagem.

Essas alterações são melhorias de apresentação e usabilidade; não constituem uma avaliação formal de satisfação do usuário.

## 11. Acessibilidade

Recursos presentes no código:

- atributo `lang="pt-BR"` nas páginas principais;
- link para pular diretamente ao conteúdo principal;
- labels associados aos campos;
- foco visível com `:focus-visible` e foco nos campos;
- uso de `aria-label`, `aria-controls`, `aria-expanded`, `aria-current` e `aria-hidden`;
- captions ocultas para tabelas;
- navegação e ações com elementos HTML semânticos;
- indicação textual dos estados, além de cores;
- regra `prefers-reduced-motion` no CSS.

Não foi executada auditoria automatizada com ferramenta especializada. Navegação manual completa por teclado e avaliação com leitor de tela permanecem [PENDENTES DE VALIDAÇÃO PELO GRUPO].

## 12. Testes

Em 18/09/2026 foi executado:

```bash
PYTHONPATH=tests ./.venv/bin/python -m unittest discover -s tests -p 'test*.py' -v
```

Resultado: **27 testes executados, 27 aprovados e nenhum falho**.

Os cenários cobertos incluem:

- login e usuários autorizados;
- regras de tutores, pets, veterinários e consultas;
- histórico clínico e inclusão de condição;
- cadastro de produto e alerta de estoque mínimo;
- entrada por lote;
- saída manual;
- estoque negativo;
- FEFO;
- lote vencido não selecionado;
- divisão de saída entre lotes;
- uso de produto em consulta;
- estorno de saída e ajuste;
- consumo médio;
- filtros de lote e movimentação;
- paginação e valor total;
- exportações CSV autenticadas;
- parâmetros inválidos de paginação;
- renderização das telas analíticas;
- API autenticada do estoque.

Os testes confirmam comportamento automatizado em ambiente isolado. Não substituem testes de aceitação com a comunidade externa.

## 13. Resultados parciais

### Resultados técnicos

- A aplicação continua executando sobre Flask, Jinja2 e SQLite.
- O módulo de estoque possui esquema, serviços, telas, regras e testes próprios.
- O histórico Git registra commits separados para evolução visual, integração de estoque, filtros, paginação, CSV, indicadores e API.
- A branch documentada está limpa após a implementação.

### Resultados funcionais

O sistema consegue cadastrar e consultar produtos, categorias e fornecedores; registrar lotes e entradas; realizar saídas manuais e clínicas; aplicar FEFO; impedir saldo negativo; registrar ajustes e estornos; exibir alertas; calcular consumo e reposição; gerar CSV; e fornecer dados básicos por API autenticada.

### Resultados de usabilidade

O sistema apresenta uma estrutura visual mais consistente, navegação lateral, informações resumidas em cards, tabelas com filtros e paginação e adaptação para telas menores. Ainda não há métrica formal de usabilidade nem feedback final registrado da clínica.

## 14. Validação com a comunidade externa

O Plano de Ação prevê nova validação com a Clínica Veterinária Fernanda Calixto, incluindo discussão sobre compras, armazenamento, uso, descarte, validade, estoque mínimo e vínculo aos atendimentos.

**[PENDENTE: inserir feedback da médica veterinária Fernanda Calixto sobre a versão parcial do sistema.]**

O grupo deve registrar data, participantes, roteiro, observações, problemas identificados e decisões tomadas a partir do feedback.

## 15. Limitações atuais

- O SQLite é adequado ao desenvolvimento e à demonstração local, mas a persistência do arquivo em hospedagem gratuita precisa ser validada antes de apresentar o deploy como solução definitiva.
- O Render está configurado em `render.yaml`, porém não há neste documento evidência de uma validação recente do ambiente publicado.
- A API criada é mínima e somente de leitura para o estoque; não é uma API completa de todos os módulos clínicos.
- A exportação CSV foi implementada; PDF foi deixado para etapa futura.
- PWA, código de barras, múltiplas clínicas, pagamentos e IA não fazem parte desta versão.
- Não há avaliação automatizada completa de acessibilidade nem teste formal de carga/concorrência.
- Não foram identificadas métricas quantitativas de redução de perdas, tempo ou custo.
- O feedback da comunidade externa e a validação de aceitação ainda estão pendentes.
- A bibliografia acadêmica precisa ser inserida pelo grupo.

## 16. Próximas etapas

Com base no Plano de Ação e no estado atual:

1. apresentar o protótipo à comunidade externa;
2. coletar e registrar feedback sobre fluxo de estoque e integração com consultas;
3. corrigir problemas encontrados sem ampliar indevidamente o escopo;
4. executar revisão de usabilidade, acessibilidade e responsividade;
5. repetir testes automatizados e acrescentar regressões quando necessário;
6. validar o deploy gratuito e documentar suas limitações;
7. revisar relatórios e evidências visuais;
8. consolidar o relatório final e o vídeo de apresentação.

## 17. Conclusão parcial

O UniVet evoluiu do sistema clínico desenvolvido no PI I para uma versão com módulo de estoque integrado à rotina de consultas. A solução parcial já reúne cadastro de produtos, fornecedores e categorias, controle por lotes, validade, entradas, saídas, FEFO, alertas, rastreabilidade, consumo, reposição, filtros, paginação, CSV e API autenticada.

As funcionalidades centrais estão cobertas por 27 testes aprovados e foram implementadas mantendo a stack original. Ainda são necessários a validação com a clínica, a inserção da bibliografia, a coleta de screenshots, a confirmação do deploy e os refinamentos finais previstos no Plano de Ação.

