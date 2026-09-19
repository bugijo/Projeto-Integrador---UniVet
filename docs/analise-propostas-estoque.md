# Análise comparativa das propostas de estoque — UniVet PI II

Data da análise: 17/09/2026  
Branch de trabalho: `feature/integracao-propostas-estoque`  
Commit de referência da base: `f03ff9d` (`style: transformar relatórios em visão analítica`)

## Escopo e evidências

Esta etapa é somente de análise. Nenhum arquivo de código, banco, rota ou regra de negócio foi alterado nesta rodada. A árvore já possuía alterações locais de rodadas anteriores; elas foram preservadas e não foram descartadas.

Fontes analisadas:

- base local `UniVet`, em Flask/Jinja2/SQLite;
- [farmacia-vet-estoque](https://github.com/marombandersonk2-dot/farmacia-vet-estoque), clonado localmente;
- [univet-estoque-veterinario](https://github.com/americodevluan/univet-estoque-veterinario), clonado localmente;
- `resumo_projeto_whatsapp.txt`;
- `PI_II_Plano_de_Ação_Grupo_1.docx` e sua cópia binária idêntica;
- `Projeto-Integrador---UniVet-main (2).zip` e sua cópia binária idêntica;
- link do aplicativo Render e link do Figma informados no briefing.

O aplicativo Render e o arquivo Figma não puderam ser inspecionados pelo acesso disponível nesta análise: ambos retornaram indisponibilidade/inacessibilidade. Por isso, não há conclusão visual baseada nessas duas fontes; as ideias atribuídas a elas ficam pendentes de validação manual.

## A. Inventário da base atual

### Arquitetura

O UniVet atual é uma aplicação monolítica server-side:

- linguagem principal: Python 3;
- framework web: Flask;
- renderização: Jinja2, HTML e CSS;
- comportamento de interface: JavaScript nativo e SVG próprio;
- banco: SQLite (`banco.db`), com criação/migração incremental em `init_db.py` e `estoque/schema.py`;
- testes: `unittest` em `tests/test_app.py` e `tests/test_estoque.py`;
- execução: `run_server.py`;
- CI/deploy: workflow GitHub em `.github/workflows/ci.yml` e configuração Render em `render.yaml`.

O núcleo clínico continua concentrado em `app.py`. O estoque já possui uma separação útil em `estoque/schema.py` e `estoque/services.py`, mas as rotas e parte da composição das telas permanecem no arquivo principal. Essa separação deve ser ampliada somente quando uma necessidade concreta aparecer.

### Funcionalidades verificadas

Já existem: autenticação, usuários autorizados, tutores, CPF, pets, veterinários, serviços, consultas, calendário, agenda do dia, histórico clínico, auditoria, produtos, categorias, fornecedores, lotes, entradas, saídas, ajustes, estornos, FEFO, vínculo com consulta, baixa automática, alertas de estoque/validade, dashboard, relatórios, consumo e sugestão transparente de reposição.

O estado atual também contempla preço de compra, margem, valor sugerido e valor praticado nos fluxos de movimentação/atendimento, em alterações locais anteriores a esta análise.

Limitações estruturais observadas:

- `app.py` é grande e acumula rotas, validações, consultas e preparação de contexto;
- não existe uma API REST pública/coesa para o estoque; há APIs pontuais para necessidades do frontend legado;
- SQLite atende muito bem à demonstração local, mas o arquivo persistido não é uma solução de nuvem durável por si só;
- a interface é responsiva e funcional, mas ainda é baseada em templates e componentes CSS próprios, sem um design system formal;
- não foram encontrados testes específicos de exportação, acessibilidade automatizada, integração em navegador ou concorrência de estoque.

## B. Análise das propostas externas

### Proposta 1 — `farmacia-vet-estoque`

O repositório contém um README, licença MIT e documentação de uma solução planejada, sem código de aplicação para integrar diretamente. O README descreve React/Vite/Bootstrap/Chart.js no frontend, Node/Express/API REST no backend, PostgreSQL/Prisma, JWT/bcrypt, Jest/Supertest, Render e soft delete.

Ideias relevantes:

- filtros, busca e paginação;
- dashboard com entradas x saídas, produtos por categoria e valor do estoque;
- exportação CSV/PDF;
- perfis ADMIN/FUNCIONARIO;
- notificações na topbar;
- bloqueio de venda/uso de item vencido;
- soft delete e health check.

Limites para o UniVet: não há implementação para reaproveitar; a troca para React/Node/PostgreSQL contrariaria a continuidade aprovada; o README informa expiração de banco gratuito do Render, portanto não é uma base segura para a apresentação sem validar o estado atual do serviço.

Recomendação: usar apenas como referência documental de requisitos e vocabulário. Não copiar a arquitetura nem migrar o projeto.

### Proposta 2 — `univet-estoque-veterinario`

É uma implementação funcional independente com frontend React/Vite/Bootstrap/Chart.js e backend Node/Express, API REST, Prisma/PostgreSQL, autenticação JWT, perfis, validação, soft delete, alertas, paginação, relatórios CSV/PDF e testes Jest/Supertest. O histórico tem 31 commits e separa controllers, routes, services, middlewares, validators e utils.

Pontos tecnicamente úteis como referência:

- transações para entradas e saídas;
- bloqueio de estoque negativo;
- bloqueio de uso/venda de vencidos e exceções para baixa;
- alertas de estoque baixo, vencido e vencendo em até 30 dias;
- dashboard com valor do estoque, movimentações mensais e distribuição por categoria;
- filtros e paginação de listagens;
- validação de entrada e saída;
- autenticação e autorização por perfil;
- soft delete administrativo;
- CSV com BOM e separador compatível com Excel;
- suíte declarada de 43 testes e deploy em Blueprint Render.

Limites para o UniVet: o modelo simplifica lotes ao manter lote/validade no produto e na entrada, não representa FEFO completo nem vínculo detalhado de item a consulta; a stack, autenticação e banco são incompatíveis com a base atual sem uma migração de grande porte; PDF/Render/PostgreSQL dependem de detalhes que precisam ser validados antes de qualquer adoção.

Recomendação: aproveitar padrões de UX e regras como referência, reproduzindo apenas o que couber no Flask/SQLite e for coberto por testes.

### Proposta 3 — materiais do WhatsApp

Os dois ZIPs têm o mesmo SHA-256 e representam a mesma fotografia do UniVet anterior. Os dois DOCX também têm o mesmo SHA-256 e representam o mesmo plano de ação. Não são quatro propostas diferentes.

O resumo confirma o escopo já implementado no PI I e a inclusão inicial do estoque. O Plano de Ação do PI II acrescenta como objetivo: estoque por lotes, integração com consultas e histórico, valores de compra, alertas, rastreabilidade, baixa automática, dashboard, relatórios, JavaScript, nuvem, API, acessibilidade, GitHub e testes. Também registra explicitamente que o módulo financeiro completo fica fora do escopo principal.

Recomendação: tratar o Plano de Ação como fonte de escopo acadêmico e critérios de aceite, e os ZIPs como referência histórica. Não reimportar os arquivos sobre a base atual.

## C. Matriz comparativa

Legenda: **JÁ TEMOS** = presente na base atual; **PROPOSTA NOVA** = aparece como requisito ainda não consolidado; **MELHOR QUE A NOSSA** = referência externa mais desenvolvida; **DUPLICADO** = mesma ideia repetida em outra fonte; **NÃO RECOMENDADO** = incompatível com o escopo/custo; **CANDIDATO À INTEGRAÇÃO** = melhoria compatível a avaliar.

| Capacidade | UniVet atual | Proposta 1 | Proposta 2 | WhatsApp/Plano | Decisão preliminar |
|---|---|---|---|---|---|
| Produto, categoria e fornecedor | JÁ TEMOS | JÁ TEMOS | JÁ TEMOS | JÁ TEMOS | Manter e melhorar UX |
| Lote, validade e quantidade por lote | JÁ TEMOS | JÁ TEMOS | Parcial | PROPOSTA NOVA consolidada | Manter FEFO atual e validar cobertura |
| Estoque mínimo e alertas | JÁ TEMOS | JÁ TEMOS | JÁ TEMOS | JÁ TEMOS | Manter |
| Entradas, saídas, ajustes e estornos | JÁ TEMOS | JÁ TEMOS | JÁ TEMOS | JÁ TEMOS | Manter |
| FEFO | JÁ TEMOS | Não demonstrado | Não demonstrado | JÁ TEMOS | Diferencial interno |
| Integração com consulta e baixa automática | JÁ TEMOS | Não demonstrado | Não demonstrado | JÁ TEMOS | Manter e testar |
| Histórico e rastreabilidade | JÁ TEMOS | JÁ TEMOS | JÁ TEMOS | JÁ TEMOS | Manter |
| Dashboard e gráficos | JÁ TEMOS | JÁ TEMOS | MELHOR QUE A NOSSA | PROPOSTA NOVA | CANDIDATO À INTEGRAÇÃO |
| Relatórios e consumo | JÁ TEMOS | JÁ TEMOS | JÁ TEMOS | JÁ TEMOS | Melhorar sem duplicar lógica |
| CSV | Parcial/pendente de validação | JÁ TEMOS na proposta | JÁ TEMOS | PROPOSTA NOVA | Priorizar se o fluxo atual não cobrir |
| PDF | Parcial/pendente de validação | JÁ TEMOS na proposta | JÁ TEMOS | Investigação | Baixa prioridade gratuita |
| Busca, filtros e paginação | Parcial | JÁ TEMOS | MELHOR QUE A NOSSA | PROPOSTA NOVA | CANDIDATO À INTEGRAÇÃO |
| Notificações e leitura | Alertas em tela | Topbar | Topbar e notificações | Alertas | Melhorar com solução local |
| Perfis e permissões | Autenticação existente | ADMIN/FUNCIONARIO | ADMIN/FUNCIONARIO | PROPOSTA NOVA | CANDIDATO À INTEGRAÇÃO |
| Auditoria/soft delete | Auditoria e estorno | Soft delete | Soft delete | Rastreamento | Avaliar por caso, sem esconder histórico |
| Valores de compra/venda | JÁ TEMOS localmente | Valor do estoque | Valor do estoque | Compra; financeiro fora do escopo | Manter financeiro simples |
| Código de barras | Não encontrado | Não demonstrado | Não demonstrado | Investigação | Futuro, não essencial |
| API | APIs pontuais | REST | REST completa | Obrigatório acadêmico | Criar API mínima sem reescrever app |
| Acessibilidade e responsividade | Base responsiva | Bootstrap | Bootstrap | Obrigatório | Testar e melhorar |
| Testes | unittest, 21 testes na referência local | Não demonstrado | Jest/Supertest declarados | Obrigatório | Ampliar testes existentes |
| Nuvem/deploy | Render configurado, SQLite | Render | Render + PostgreSQL | Obrigatório | Validar gratuito e persistência |
| Reposição por histórico | JÁ TEMOS sugestão simples | Não demonstrado | Não demonstrado | PROPOSTA NOVA | Manter transparente e simples |

## D. Parecer de consolidação

### Manter — plano A

- Flask, Jinja2, HTML/CSS/JavaScript e SQLite;
- cadastros e agenda clínica existentes;
- produtos, categorias, fornecedores, lotes e movimentações;
- FEFO, estoque não negativo, estorno e rastreabilidade;
- integração com consultas e histórico clínico;
- alertas de mínimo e validade;
- consumo, reposição transparente, dashboard e testes.

### Melhorar a partir das referências — plano B

- busca, filtros e paginação onde a listagem justificar;
- hierarquia do dashboard e gráficos simples;
- alertas agrupados com estado lido/não lido, sem serviço pago;
- permissões explicitamente documentadas;
- exportação CSV gerada localmente e, somente se viável, PDF;
- cobertura de testes de regras e acessibilidade.

### Adicionar — plano C

- tela de movimentações mais analítica;
- visão de lotes por produto com validade, saldo e valor;
- vínculo visível de cada saída clínica à consulta/pet;
- indicadores de consumo e sugestão de reposição baseada no histórico;
- API mínima documentada para demonstrar o requisito acadêmico.

### Não integrar — plano D

- migração para React/Node/PostgreSQL/Prisma;
- dependência de APIs externas pagas ou com cartão;
- módulo financeiro completo, emissão fiscal, pagamentos e vendas complexas;
- scanner/barcode antes de cobrir os fluxos essenciais;
- cópia direta de código ou de telas dos repositórios externos.

### Futuro — plano E

- PWA instalável/offline;
- importação em massa;
- PDF mais elaborado;
- previsão de demanda mais avançada;
- código de barras;
- múltiplas unidades e permissões granulares.

## E. Critérios para implementação futura

Uma ideia somente deve entrar após responder positivamente: resolve uma dor real da clínica; cabe na arquitetura Flask atual; não duplica uma função existente; é explicável academicamente; cabe no semestre; usa tecnologia gratuita; tem teste e não quebra os fluxos atuais.

Nenhuma integração externa está aprovada nesta fase. A primeira opção é sempre implementação local com ferramentas já presentes. Se houver necessidade de serviço, documentar previamente serviço, finalidade, plano gratuito, limitações e alternativa gratuita.

