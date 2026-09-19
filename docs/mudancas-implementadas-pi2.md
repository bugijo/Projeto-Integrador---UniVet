# Mudanças implementadas no PI II

Linha do tempo baseada no histórico Git da branch `feature/integracao-propostas-estoque`.

| Data | Commit | Funcionalidade/mudança | Motivo | Arquivos ou áreas principais | Resultado |
|---|---|---|---|---|---|
| 2026-05-19 | `116a882` | Menu hambúrguer e layout responsivo mobile | Permitir navegação em telas menores | `static/style.css`, JavaScript de navegação | Base mobile aprimorada |
| 2026-05-20 | `b23c198` | Cache-bust do CSS | Garantir carregamento da versão visual atualizada | templates/configuração de assets | Alterações visuais passam a ser recarregadas |
| 2026-08-29 | `33f45bb` | Módulo inicial de controle de estoque | Atender necessidade de continuidade do PI II | `app.py`, `init_db.py`, templates de estoque | Base do módulo criada |
| 2026-09-01 | `dd480fa` | Protótipo inicial do estoque | Estruturar primeiras telas do fluxo | templates e estilos | Fluxo inicial navegável |
| 2026-09-01 | `e4bb082` | Telas do módulo de estoque | Cobrir produtos, lotes e movimentações | templates/estoque | Cobertura visual ampliada |
| 2026-09-01 | `8cf26e0` | Revisão e validação do protótipo | Corrigir inconsistências antes do refinamento | aplicação e templates | Protótipo estabilizado |
| 2026-09-01 | `3163de7` | Design system UniVet 2.0 | Uniformizar componentes e identidade visual | `static/style.css`, templates base | Padrões visuais compartilhados |
| 2026-09-01 | `ec8b02f` | Harmonização de telas e estados vazios | Melhorar consistência e feedback de listas | templates e CSS | Estados mais claros |
| 2026-09-03 | `1f1b158` | Refinamento de composição e datas | Melhorar hierarquia visual e formato brasileiro | templates e CSS | Interface mais consistente |
| 2026-09-03 | `f03ff9d` | Relatórios em visão analítica | Exibir consumo, ranking e indicadores | relatório, CSS e templates | Relatório com leitura analítica |
| 2026-09-17 | `56c1c19` | Preservação do estado aprovado e documentação comparativa | Registrar o estado antes da integração | `docs/` e alterações locais anteriores | Ponto de segurança documentado |
| 2026-09-17 | `f6b063b` | Filtros, paginação, CSV, valor estimado e indicadores | Integrar ideias selecionadas das propostas externas | `app.py`, `estoque/services.py`, templates e testes | Primeira etapa de integração concluída |
| 2026-09-17 | `6ba9791` | Registro da execução da integração | Manter rastreabilidade acadêmica | `docs/integracao-propostas-estoque.md` | Origem e testes documentados |
| 2026-09-17 | `255d951` | API autenticada do estoque | Demonstrar requisito de API sem mudar a stack | `app.py`, testes e documentação | Resumo, produtos e movimentações expostos em JSON |

## Observação sobre autoria e origem

As alterações acima representam o histórico Git disponível no repositório. A atribuição individual de cada commit ou atividade permanece [PENDENTE DE PREENCHIMENTO PELO GRUPO] quando não estiver explícita no histórico.

