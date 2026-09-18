# Plano de integração das propostas de estoque — UniVet PI II

Este documento registra o que poderá ser implementado depois da aprovação da análise. Nesta rodada não houve implementação.

## 1. Diretriz arquitetural

Preservar Python/Flask/Jinja2/JavaScript/HTML/CSS/SQLite. O estoque continuará incrementalmente separado em `estoque/schema.py` e `estoque/services.py`; novas rotas e responsabilidades só serão extraídas quando isso reduzir acoplamento de uma tarefa real. Não migrar para React, Node, Prisma ou PostgreSQL.

O banco permanece SQLite para desenvolvimento e demonstração. A configuração de nuvem deverá ser avaliada quanto à persistência do arquivo; não se deve prometer persistência permanente em hospedagem gratuita sem uma estratégia gratuita validada.

## 2. Tabela de rastreabilidade das ideias

| IDEIA | ORIGEM | COMO ERA | COMO FOI INTEGRADA/PROPOSTA | RESULTADO ESPERADO |
|---|---|---|---|---|
| Estoque por lotes | Plano de Ação; base atual | Produto e lotes já existem | Preservar o modelo atual e validar saldo, validade e FEFO | Rastreabilidade por lote |
| Saída ligada a consulta | Plano de Ação; base atual | Já há uso em consulta | Tornar vínculo e histórico mais visíveis | Baixa automática explicável |
| FEFO | Base atual | Regra já implementada | Não substituir por versão externa | Consumo do lote mais próximo do vencimento |
| Alertas de mínimo/validade | Base atual; duas propostas externas | Alertas já existem | Refinar apresentação e cobertura de testes | Menos faltas e perdas |
| Dashboard com gráficos | Base atual; propostas 1 e 2 | Dashboard e visão analítica já existem | Ajustar composição e indicadores com dados existentes | Decisão rápida da clínica |
| Busca, filtros e paginação | Propostas 1 e 2 | Parcialmente presente | Adicionar apenas nas telas com volume real | Navegação mais eficiente |
| CSV | Propostas 1 e 2; Plano de Ação | Avaliar cobertura atual | Preferir geração local, sem API paga | Exportação demonstrável |
| PDF | Propostas 1 e 2 | Não tratar como essencial | Deixar como prioridade 3 se exigir dependência nova | Relatório apresentável |
| Perfis/permissões | Proposta 2; Plano de Ação | Login existente | Formalizar ações administrativas críticas | Segurança acadêmica demonstrável |
| Auditoria/estorno | Base atual; proposta 2 | Auditoria/estorno já existem | Preservar histórico e testar reversão | Rastreabilidade sem apagar fatos |
| Valor de estoque | Propostas 1 e 2; evolução local | Compra/venda já estão no protótipo | Exibir somente indicadores simples | Apoio à gestão, sem financeiro completo |
| Reposição por histórico | Base atual; Plano de Ação | Sugestão simples e transparente | Melhorar explicação, sem modelo preditivo complexo | Sugestão compreensível |
| API | Plano de Ação; proposta 2 | Existem endpoints pontuais | Criar contrato mínimo para dados do estoque, se aprovado | Evidenciar requisito web/API |
| Responsividade e acessibilidade | Plano de Ação; propostas externas | CSS responsivo existente | Checklist e testes manuais/automatizados | Uso em desktop e celular |

## 3. Ordem de implementação aprovada para a próxima fase

### Etapa 1 — estabilização

Registrar o estado atual, separar os commits locais anteriores quando possível, executar a suíte completa e criar casos de regressão para estoque negativo, FEFO, validade, estorno, vínculo com consulta e valores.

### Etapa 2 — visão por lote

Revisar as telas de produto, lote, entrada e movimentação para que saldo, validade, fornecedor, custo e valor sugerido sejam compreensíveis. Não alterar a regra de negócio sem teste correspondente.

### Etapa 3 — integração clínica

Aprimorar a seleção de produtos usados no atendimento, registrar item/lote/quantidade/valor praticado e garantir que o prontuário permaneça acessível. O estorno deve ser explícito e auditável.

### Etapa 4 — indicadores

Consolidar dashboard de estoque com estoque baixo, vencimentos, quantidade total, consumo recente, movimentações e reposição. Reutilizar consultas existentes; gráficos devem ser leves e legíveis.

### Etapa 5 — filtros e exportação

Aplicar filtros/paginação nas listas de maior volume. Implementar CSV local caso esteja pendente. PDF fica condicionado a uma biblioteca gratuita, estável e sem custo operacional.

### Etapa 6 — API e nuvem

Documentar uma API pequena e coerente para demonstrar o requisito do PI II. Validar deploy sem adotar banco pago ou solução que exija cartão. A limitação de persistência do SQLite deve aparecer na documentação e na apresentação.

### Etapa 7 — validação

Executar testes automatizados, checklist de acessibilidade, testes em viewport desktop/celular e validação com a comunidade externa. Cada item deve ter commit separado, origem registrada e evidência.

## 4. Prioridades

### PRIORIDADE 1 — essencial para o PI II

- preservar e testar produtos, categorias, fornecedores, lotes, entradas, saídas e estornos;
- garantir não negativação, FEFO, validade e rastreabilidade;
- integração consulta → item utilizado → baixa automática → histórico;
- dashboard com alertas e indicadores essenciais;
- acessibilidade e responsividade verificadas;
- testes de regressão;
- documentação de API, Git/GitHub e deploy gratuito;
- validação com a clínica.

### PRIORIDADE 2 — importante e viável

- busca, filtros e paginação;
- CSV;
- permissões mais explícitas;
- notificações locais e agrupamento de alertas;
- visão detalhada de lotes;
- indicadores de consumo e reposição;
- melhorias de UX em formulários e tabelas.

### PRIORIDADE 3 — diferencial

- PDF;
- PWA;
- importação em massa;
- código de barras;
- previsão avançada de demanda;
- permissões granulares e múltiplos depósitos.

## 5. Riscos e limites

- O repositório Render analisado como referência usa PostgreSQL gratuito com limitações que podem mudar; não é uma dependência aprovada.
- O aplicativo Render informado não pôde ser acessado nesta análise.
- O Figma informado não pôde ser acessado nesta análise; sua proposta visual precisa de revisão manual antes de atribuir qualquer decisão a ela.
- O material do WhatsApp contém duplicatas binárias; elas não devem gerar tarefas duplicadas.
- O working tree da base não estava limpo antes da criação desta branch. As alterações locais foram preservadas; não houve reset nem alteração da `main`.

## 6. Critério de conclusão da integração

Uma entrega futura só será considerada concluída quando houver: funcionalidade implementada na stack atual; teste automatizado ou evidência manual adequada; regressão executada; documentação da origem e adaptação; revisão visual desktop/celular; verificação de acessibilidade; e commit separado com mensagem clara.

## 7. Execução — primeira etapa integrada

Commit: `feat: integrar filtros paginacao e exportacoes do estoque`.

| Funcionalidade | Origem | Situação anterior | Adaptação realizada | Arquivos principais | Testes | Resultado |
|---|---|---|---|---|---|---|
| Filtros de produtos, lotes e fornecedores | Propostas 1 e 2 | Produtos tinham filtros básicos; lotes não separavam vencidos; fornecedores não filtravam status | Filtros foram adicionados no backend e preservados nas telas | `estoque/services.py`, `app.py`, templates de produtos/lotes/fornecedores | Filtros inválidos e telas renderizadas | Integrado |
| Filtros de movimentações | Proposta 2 | Havia produto, tipo e período | Adicionados usuário e consulta, mantendo histórico clínico | `estoque/services.py`, `app.py`, template de movimentações | Teste de filtros e regressão | Integrado |
| Paginação | Propostas 1 e 2 | Listagens carregavam todos os registros | Paginação opcional com limite seguro, anterior/próxima e preservação da querystring | `estoque/services.py`, `app.py`, `templates/_paginacao.html` | Paginação, parâmetros inválidos e smoke HTTP | Integrado |
| Exportação CSV | Propostas 1 e 2; Plano de Ação | Não havia exportação consolidada | Criados CSV local de movimentações, posição e consumo, com BOM UTF-8 e separador `;` | `app.py`, templates de produtos/movimentações/relatórios | Três endpoints autenticados | Integrado |
| Valor estimado do estoque | Propostas 1 e 2; briefing aprovado | Havia valor por lote/produto, mas não indicador consolidado | Soma `quantidade_atual × valor_compra_unitario` dos lotes ativos no dashboard, relatório e CSV | `estoque/services.py`, dashboard, relatório | Teste de valor do estoque e smoke | Integrado |
| Indicadores de consumo e reposição | Base atual; Plano de Ação | Existiam no relatório | Reapresentados no dashboard sem criar nova regra de negócio | `app.py`, `templates/estoque/dashboard.html` | Smoke do dashboard e suíte completa | Integrado |

### Validação desta etapa

- Sintaxe Python validada com `py_compile`.
- `git diff --check` sem erros.
- Suíte completa: 26 testes aprovados.
- Testes novos: exportações CSV autenticadas, filtros/paginação inválidos, telas analíticas, paginação de serviços, valor consolidado e filtros de lote/movimentação.
- Nenhuma tecnologia externa, serviço pago ou banco novo foi adicionado.
