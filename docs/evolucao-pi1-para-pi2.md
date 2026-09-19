# Evolução do UniVet: PI I para PI II

Documento de apoio ao Relatório Parcial. As descrições abaixo refletem o estado verificável da branch `feature/integracao-propostas-estoque` em 18/09/2026.

| Item | Como era no PI I | Como ficou no PI II | Justificativa da mudança | Evidência no sistema |
|---|---|---|---|---|
| Aparência geral | Interface funcional do sistema clínico inicial | Identidade visual UniVet 2.0 com sidebar, topbar, cards, estados e layout responsivo | Melhorar leitura e uso diário sem trocar a stack | `static/style.css`, `templates/base.html`, commits `8bf8b11`, `3163de7`, `ec8b02f` |
| Dashboard | Agenda e informações operacionais clínicas | Dashboard clínico com agenda, KPIs e resumo de estoque; dashboard de estoque separado | Aproximar a visão inicial das decisões da rotina | `templates/pagina_inicial.html`, `templates/estoque/dashboard.html` |
| Estoque | Não fazia parte do núcleo original documentado | Módulo integrado com produtos, lotes, movimentações e análise | Necessidade central registrada no Plano de Ação | `estoque/schema.py`, `estoque/services.py`, rotas `/estoque` |
| Produtos | Cadastros clínicos do PI I | Produto com tipo, categoria, unidade, código, estoque mínimo e margem | Padronizar itens utilizados pela clínica | `templates/estoque/produtos`, `app.py` |
| Categorias | Não havia cadastro específico de estoque | Cadastro, edição, busca e ativação/inativação | Organizar produtos e relatórios | `categorias` em `estoque/schema.py` e rotas correspondentes |
| Fornecedores | Não havia cadastro específico de estoque | Cadastro, edição, busca, filtro por status e paginação | Registrar origem das entradas | `fornecedores` em `estoque/schema.py`, tela de fornecedores |
| Lotes | Não havia controle por lote | Cada entrada cria lote com saldo, validade, custo e venda sugerida | Permitir rastreabilidade e FEFO | tabela `lotes`, `registrar_entrada` |
| Validade | Não havia alerta de validade para estoque | Alertas de vencimento e próximos vencimentos; lotes vencidos não entram no FEFO | Reduzir risco operacional de uso de item vencido | `resumo_estoque`, `listar_lotes`, regras em `registrar_saida_fefo` |
| Entradas | Não havia movimentação de estoque | Entrada com fornecedor, lote, quantidade, validade, custo e usuário | Atualizar saldo e registrar origem | `registrar_entrada`, `/estoque/lotes/entrada` |
| Saídas | Não havia saída integrada | Saída manual distribuída por FEFO, com motivo e valor praticado | Registrar consumo e repasse real | `registrar_saida_fefo`, `/estoque/saidas` |
| Ajustes | Não havia ajuste de inventário | Ajuste de lote com motivo e variação registrada | Corrigir divergências físicas mantendo histórico | `registrar_ajuste`, `/estoque/lotes/<id>/ajuste` |
| Estornos | Não havia estorno de estoque | Estorno de saída/ajuste com vínculo à movimentação original | Corrigir operações sem apagar rastreabilidade | `registrar_estorno`, rota de estorno |
| FEFO | Não existia | First Expire, First Out: lote válido com menor validade é utilizado primeiro | Priorizar segurança e reduzir perdas | consultas ordenadas por validade em `estoque/services.py` |
| Integração com consultas | Consultas e histórico clínico já existiam | Produtos podem ser registrados como utilizados em consulta | Relacionar consumo ao atendimento | `itens_consulta`, rota `/consultas/<id>/produtos` |
| Baixa automática | Não havia baixa de estoque | Uso em consulta reduz saldo e registra lote/movimentação | Evitar atualização manual duplicada | `registrar_uso_consulta` |
| Rastreabilidade | Auditoria clínica já existia | Movimentação guarda produto, lote, tipo, quantidade, usuário, consulta e origem de estorno | Identificar o caminho do item | tabela `movimentacoes_estoque`, tela de histórico |
| Alertas | Não havia alertas de estoque | Alertas de estoque abaixo do mínimo e validade | Apoiar reposição e acompanhamento | `resumo_estoque`, dashboard e relatórios |
| Relatórios | Relatórios clínicos/operacionais do PI I | Relatório de consumo, ranking, série diária, reposição e valor de estoque | Transformar movimentações em informação de apoio | `templates/estoque/relatorios.html`, `relatorio_consumo` |
| Análise de consumo | Não existia no escopo inicial | Consumo por produto e por dia em períodos de 7 a 365 dias | Identificar uso recente | `consumo_por_produto`, `historico_consumo_diario` |
| Sugestão de reposição | Não existia | Regra transparente baseada em estoque mínimo e média de consumo | Sugerir reposição explicável, sem IA | `sugestao_reposicao` |
| Filtros | Filtros clínicos existentes | Busca/filtros de produto, lote, movimentação, fornecedor e relatório | Trabalhar com volume maior de dados | `app.py`, templates de estoque |
| Paginação | Não era aplicada ao estoque | Paginação de produtos, lotes, movimentações e fornecedores | Evitar carregar todas as linhas | `templates/_paginacao.html`, `_paginacao` |
| Exportações | Não havia exportação do estoque | CSV de movimentações, posição e consumo | Facilitar análise e evidência acadêmica sem custo | rotas `/estoque/exportar/*.csv` |
| API | APIs pontuais da aplicação clínica | API autenticada de resumo, produtos e movimentações | Demonstrar requisito de API sem reescrever Flask | `/api/estoque/resumo`, `/api/estoque/produtos`, `/api/estoque/movimentacoes` |
| Acessibilidade | Base funcional inicial | `lang`, skip link, labels, foco visível, `aria-*`, captions, reduced motion | Melhorar acesso por teclado e leitores | `templates/base.html`, `static/style.css` |
| Responsividade | Melhorias mobile já iniciadas | Sidebar móvel, tabelas com rolagem, grids e formulários adaptáveis | Atender desktop, tablet e celular | `static/style.css`, `static/js/navigation.js` |
| Testes | Testes do PI I | 27 testes, incluindo estoque, integração, CSV, API e regressões | Evitar perda das funções existentes | `tests/test_app.py`, `tests/test_estoque.py` |
| Organização do código | Núcleo mais concentrado em `app.py` | Separação parcial em `estoque/schema.py` e `estoque/services.py` | Isolar esquema e regras sem grande reescrita | diretório `estoque/` |

## Síntese

O PI II não substituiu a aplicação do PI I. Ele ampliou a solução existente com um módulo de estoque integrado ao fluxo clínico, preservando Flask, Jinja2, SQLite e os módulos de tutores, pets, consultas, agenda, histórico, serviços e veterinários.

