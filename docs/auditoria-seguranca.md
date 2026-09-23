# Auditoria defensiva e prontidão de produção — UniVet

## Atualização de homologação remota — 23/09/2026

| Evidência | Resultado | Limite |
|---|---|---|
| Neon | **PARCIALMENTE VALIDADO** | Organização Free e dois projetos separados criados pela CLI oficial; MCP Neon não ficou exposto como ferramenta callable nesta sessão. |
| Migrations | **PASSOU** | Schema aplicado remotamente em Demo e Clínica com SSL `verify-full`; não valida ainda o serviço publicado. |
| Isolamento | **PASSOU no banco** | Demo tem apenas dados fictícios seed; Clínica não recebeu seed demo nem dados reais. |
| Backup | **PARCIAL** | `pg_dump` remoto gerado com cliente PostgreSQL 17 descartável; restore em banco separado ainda inconclusivo. |
| Render Clínica | **NÃO CRIADO** | Evitado por risco do plano Free e por ainda não haver homologação de recuperação/headers. Demo existente não foi alterado. |

Os bloqueadores SEC-10, SEC-11 e SEC-15 permanecem para liberação clínica. A existência de bancos Neon não equivale a persistência/recovery homologados do serviço web. Nenhuma conta `DrFernanda` foi criada.

## Atualização corretiva — 22/09/2026

Branch `security/demo-producao-isolados`, sucessora local da branch de contexto por solicitação do roteiro. Nenhum deploy/push, conta real ou importação real. **NÃO APTO PARA DADOS REAIS**; esta atualização substitui as afirmações de estado do relatório inicial abaixo, que fica preservado como evidência anterior.

| Achado | Estado atual | Evidência e limite |
|---|---|---|
| SEC-01 | RESOLVIDO localmente | Schema sem demo por padrão, preserva contas, recusa seed em produção; `test_environments` prova banco limpo/credencial demo recusada. Serviços reais não alterados. |
| SEC-02 | RESOLVIDO localmente | Segredo obrigatório, sem fallback público em produção; teste de boot/configuração. |
| SEC-03 | RESOLVIDO localmente | Sessões no banco, revogação, autorização por perfil e sessão isolada por ambiente; `test_security`, `test_first_access`. Equipe compartilha pacientes da mesma clínica, não é multitenant. |
| SEC-04 | RESOLVIDO localmente | CSRF global inclusive login/logout/senha; templates e regressão. |
| SEC-05/06 | RESOLVIDOS localmente | Lock antes da leitura, estorno único, testes 2/5/10 conexões e operações mistas. |
| SEC-07 | RESOLVIDO no escopo testado | Secure/HSTS HTTPS, CSP com nonce, cache no-store, inatividade, limites distribuídos pelo banco. Timing de enumeração e operação real não integralmente avaliados. |
| SEC-08 | RESOLVIDO localmente | Neutralização de fórmulas textuais no CSV e exportação restrita ao administrador. |
| SEC-09 | PENDENTE — MÉDIO | Finitude, limites e validações corrigidos; precisão REAL/float e revisão completa dos campos ainda pendentes. |
| SEC-10 | BLOQUEADOR | SQLite efêmero recusado em produção/Render; adaptação PostgreSQL, migrações e restore foram validados apenas localmente. Não há provedor remoto persistente homologado. |
| SEC-11 | BLOQUEADOR de liberação | Serviço Render `univet` está na `main`, commit `95d1369`, sem serviço Clínica separado. URL responde HTTPS, mas headers de segurança esperados não foram confirmados remotamente. |
| SEC-12 | PENDENTE — MÉDIO / restrição de publicação | PDFs continuam em ancestralidade remota; requer decisão/autorização específica de saneamento. |
| SEC-13 | PENDENTE — ALTO | Agenda e histórico de cadastros atômicos, lastrowid, cancelamento sem apagar consulta, preservação de concluídas/condições/autoria. Política de adendos/edição de prontuários concluídos e constraints legadas ainda não concluída. |
| SEC-14 | PENDENTE — MÉDIO | Consumo bruto e efeito de estornos ainda precisam semântica explícita/validação. |
| SEC-15 | PENDENTE — ALTO | Documentação e restore local ampliados; responsáveis, retenção, destino externo e ensaio do ambiente real não confirmados. |

Contagem de pendências nesta classificação de liberação: **2 bloqueadores, 2 altos, 3 médios, 0 baixos**. Não é contagem de toda vulnerabilidade possível. Resolvido localmente não afirma que a correção foi implantada.

### Verificação remota somente leitura

Em 22/09/2026, o workspace Render confirmado foi consultado sem mutação. Existe somente o serviço UniVet identificado como `univet`, plano Free, branch `main`, região Oregon, URL `https://univet.onrender.com`, sem PostgreSQL Render no workspace. O deploy live informado pelo Render é o commit `95d1369`. Um `HEAD /login` retornou 200 via HTTPS, porém a resposta observada não apresentou CSP, `X-Content-Type-Options`, `Referrer-Policy`, `Permissions-Policy`, proteção contra frame ou HSTS. Não foram inspecionados valores de variáveis, não houve login, deploy, restart, alteração de banco ou criação de conta.

Checkpoint final: **77 testes passaram (27 anteriores +50), 0 falhas, 18,673 s**, sem depender de PYTHONPATH, inclusive primeiro acesso HTTPS e restart em produção fictícia. Log `artifacts/final-ci-command-tests.log`. Backup/restore compara schema/conteúdo de tabelas fictícias, não apenas contagens; concorrência inclui ajuste, estorno, saída e uso clínico. Navegador local anterior confirmou login/formulários e XSS escapado sem execução. Mudanças posteriores de primeiro acesso ainda precisam QA visual final.

Carga: uma regressão PostgreSQL de timestamp foi corrigida e coberta por teste; a validação pós-correção passou em 14 testes HTTP PostgreSQL. Na carga local descartável pós-correção, os perfis de 1/5 usuários não tiveram falhas; perfis maiores e o soak de 120 s usaram a mesma conta `admin` e foram limitados pela proteção de login (10 tentativas/conta/15 min), portanto não são uma aprovação de capacidade. A carga final com contas fictícias independentes, duração de 10–20 min e execução remota permanece pendente. O soak histórico de 600 s com snapshot anterior teve 1 timeout em 37.680; não está aprovado. Fonte e limites em `relatorio-carga.md`.

Codex Security: incompatibilidade de Node contornada por Node22 temporário, versão 0.1.29. Help/schema e dry-run antes/depois executados; `authentication.verified=false`. **Nenhum scan efetivo**, nenhuma garantia de gratuidade assumida, nenhuma API paga usada. `pip-audit` atual, após Psycopg/Alembic, encontrou zero vulnerabilidades conhecidas. Bandit atual encontrou 4 médios/22 baixos e zero altos: bind local, identificadores SQL internos e subprocessos controlados de testes; foram revisados como não exploráveis por entrada HTTP, mas permanecem no relatório do scanner. Artefatos em `artifacts/` são ignorados.

## Relatório inicial preservado — 19/09/2026

Data: 19/09/2026. Código-base: `95d13691c274e92ecd7abd5d8f43a3a911881825`.
Branch da análise: `chore/contexto-auditoria-producao`. Nenhuma correção de aplicação, alteração de banco real, push ou deploy nesta rodada.

## Parecer

**Não liberar uso com dados reais de clínica nesta versão.** O protótipo possui controles úteis e testes funcionais, mas há bloqueadores de credenciais, sessões, CSRF, integridade concorrente e armazenamento. A aprovação anterior de “deploy validado” foi mais ampla que a evidência disponível: CI verde e um GET de login não confirmam commit ativo, persistência ou prontidão clínica.

## Escopo e método

Inspeção orientada por busca de `app.py`, `init_db.py`, `estoque/`, templates/JS, dependências, CI, Render e histórico Git. Mapeadas 54 declarações de rota: 51 com `login_obrigatorio`; públicas `/`, `/login` e `/logout`. O static do Flask não integra essa contagem. Revisados autenticação/autorização, CSRF, XSS/DOM, SQL, sessões/cookies, headers/cache, API/CSV, validações, integridade/transações, privacidade, segredos, dependências e operação.

`docs/audit_local.py` reproduz cenários com banco temporário e conexões independentes. Não recebe URL externa nem usa `banco.db` real. Saída JSON é caracterização, não aprovação de controles: uma falha confirmada também produz execução bem-sucedida do script. Não foram feitos login, escrita ou carga na produção. A única requisição HTTP externa da aplicação nesta rodada foi GET `/login` na URL conhecida.

O anexo remete a uma “tarefa principal” de auditoria sem fornecer outro roteiro separado; o escopo foi derivado das áreas explicitamente listadas nele e dos requisitos anteriores do UniVet. Acesso administrativo ao Render, base real, configuração efetiva de secrets, métricas de produção e avaliação jurídica não estão disponíveis. Não é certificação de segurança nem teste de penetração exaustivo.

## Evidências reproduzidas

Comando: `PYTHONPATH=.:tests .venv/bin/python docs/audit_local.py > artifacts/audit-local.json 2> artifacts/audit-local.err`.

| Verificação | Resultado desta rodada |
|---|---|
| Anônimo em estoque, API, prontuário e CSV | 302 para login, sem acesso autorizado |
| Entrada de SQL injection no login | Não autenticou; busca de API respondeu sem erro |
| Conteúdo de script em categoria | Escapado no HTML renderizado; sem execução de navegador nesta prova |
| POST com Origin externo e sem token CSRF | Categoria persistida |
| Sessão após desativar usuário no banco | API continuou respondendo 200 |
| Veterinária altera catálogo | Categoria persistida; não existe separação de privilégios por operação |
| Campo de produto `=1+1` no CSV | Exportado como fórmula sem neutralização |
| Estoque mínimo `inf` | Aceito e armazenado |
| Dois pedidos simultâneos de 7, saldo inicial 10 | Um aceito, outro recusado; saldo e movimentos = 3 |
| Dois estornos simultâneos da mesma saída de 3 | Ambos aceitos; saldo 7 foi para 13, deveria retornar a 10 |
| Dois ajustes simultâneos, saldo 10 para 12/13 | Saldo final observado 12; soma dos movimentos 15 |
| Reinicialização de banco fictício | Excluiu usuário adicional e redefiniu hash de senha |
| Backup/restore de banco fictício | integrity_check=ok; 0 erros de FK; contagem de produtos igual |
| Exercício local limitado | 30 GETs sequenciais de API, 0 erros, mediana 2,17 ms e p95 2,90 ms |

Concorrência de estorno/ajuste foi sincronizada imediatamente depois da leitura existente, antes de `BEGIN IMMEDIATE`, por um adaptador de conexão no script. Isso força uma intercalação possível, sem modificar o código de negócio. A ordem e o saldo final do ajuste podem variar; a divergência do histórico é o critério. O exercício de 30 GETs usa test client, Linux e poucos dados demo: não mede rede, Gunicorn, múltiplos processos ou capacidade do Render.

## Achados e retestes propostos

### SEC-01 — Contas públicas e inicialização destrutiva — crítica para uso real

Evidência: `init_db.py:63`, `:88`, `:254`, `:299`; `app.py:59`. As contas demo têm senhas no código; inicialização redefine hashes/reativa contas e apaga usuários fora da lista. Seeds são chamados sem separar desenvolvimento e produção. Caminho de auto-inicialização pode executar isso em banco vazio ou schema considerado incompleto. Reprodução confirma reset/exclusão em banco descartável; não foi testado login demo online.

Impacto: acesso indevido se essas contas existirem no serviço; perda de contas e autoria operacional durante reinicialização. Propor migrações sem seeds, bootstrap administrativo privado de execução única e demo opt-in. Reteste: migrar duas vezes uma cópia fictícia com usuários personalizados sem mudar senhas, atividade ou contagens; banco de produção não conter credenciais demo.

### SEC-02 — Chave de sessão com fallback público — crítica se fallback estiver ativo

Evidência: `app.py:56`. Ausência de `SECRET_KEY` usa constante pública e permite assinar sessões com privilégios conhecidos por quem tem o código. `render.yaml` declara geração de segredo, mas aplicação efetiva do manifesto no serviço não foi confirmada. Propor falhar na inicialização de produção sem segredo privado, rotação e revogação. Reteste: ausência/valor demo impedem boot em modo produção; cookie assinado pela chave antiga recusado. Não reproduzir valores em relatórios.

### SEC-03 — Sessões não revogadas e privilégios amplos — alta

Evidência: `app.py:84`, `:196`, `:210`, `:501`. Login verifica `ativo`, mas requisições posteriores confiam em ID/perfil guardados no cookie, sem revalidar existência/atividade. Veterinária e admin têm o mesmo acesso às rotas protegidas, inclusive catálogo, exportações e operações financeiras. Não há matriz de permissões formal; acesso amplo é fato, atribuição de cada operação ainda requer decisão do projeto.

Propor autorização central por usuário ativo, versão de sessão e matriz de papéis. Reteste: desativação, remoção, troca de senha/perfil revogam acesso; veterinária e admin recebem respostas coerentes com a matriz aprovada em HTTP e API.

### SEC-04 — Falta de CSRF — alta

Evidência: `app.py:739` e demais POSTs, templates sem token, ausência de middleware de validação. POST de origem externa sem token persistiu dados na prova local. Não houve navegação cross-site em navegador real; políticas SameSite do navegador podem limitar certas formas de ataque, sem substituir proteção no servidor. Logout usa GET (`app.py:1938`), e login também não valida CSRF.

Propor token validado no servidor para operações mutáveis, incluindo login; logout por POST. Reteste: ausência/token incorreto rejeitam sem persistir; forms válidos e JS continuam funcionais.

### SEC-05 — Estorno duplicado concorrente — alta

Evidência: `estoque/services.py:461`, `estoque/schema.py:54`. Consulta de estorno prévio ocorre antes do lock; não há unicidade da origem para estornos. Prova: dois estornos bem-sucedidos para a mesma saída. Propor leitura/validação dentro da transação e restrição de unicidade adequada. Reteste com conexões independentes: exatamente um estorno, saldo volta ao original, segundo pedido recebe erro de negócio.

### SEC-06 — Ajuste concorrente descola saldo do histórico — alta

Evidência: `estoque/services.py:407`. Saldo e diferença são calculados antes de `BEGIN IMMEDIATE`; update posterior define saldo absoluto com diferença antiga. Prova: saldo 12 e histórico 15. Propor ler/calcular dentro da transação, ou controle de versão com comparação do saldo original. Reteste: toda intercalação mantém saldo igual à soma das variações e identifica conflitos.

### SEC-07 — Cookies, cache, tentativas e headers incompletos — média/alta conforme exposição

Evidência: configuração de `app.py:55` e login `:491`. Localmente HttpOnly está presente; Secure e SameSite não foram emitidos. Não há política explícita de inatividade, limite de tentativas, CSP, proteção contra framing ou cache de páginas privadas. Ausência foi avaliada no código e respostas locais, sem ataque de força bruta. O proxy online observado fornece `X-Content-Type-Options: nosniff`, portanto não atribuir ausência local automaticamente à produção.

Propor Secure em HTTPS, SameSite explícito, sessão expirada/revogável, limitação de tentativas sem bloqueio abusável, cache privado/no-store e headers compatíveis com scripts/templates existentes. Reteste de cookies HTTPS, expiração, várias falhas limitadas localmente, clickjacking e CSP sem quebrar tela.

### SEC-08 — Fórmula em CSV — média

Evidência: `app.py:114`, `:1060`. `csv.writer` escapa delimitadores, mas não fórmulas de planilha. Usuário autenticado pode cadastrar texto e induzir outro usuário a abrir exportação. Propor neutralizar campos textuais com prefixos perigosos (=,+,-,@ e controles), preservando números legítimos. Reteste com células adversariais em todos os CSVs e planilhas usadas pela equipe. A prova usou fórmula inofensiva, sem acesso externo.

### SEC-09 — Valores não finitos e limites insuficientes — média

Evidência: `app.py:630`, `estoque/services.py:22`, `:32`, `:407`. Conversão float e comparação com zero não rejeitam infinito/NaN. `inf` foi persistido como estoque mínimo. Precisão financeira usa REAL/float. Propor finitude, limites por campo e quantização monetária coerente; validar datas, IDs inexistentes e comprimentos no servidor. Reteste de NaN/±inf, negativos, extremos, campos longos e FK inválida; nada inválido deve persistir nem gerar 500. Não foram explorados payloads grandes.

### SEC-10 — Persistência incompatível com configuração declarada — crítica para dados reais

Evidência: `app.py:40` usa SQLite local; `render.yaml:5` declara free, sem volume persistente nem banco externo. O Render documenta filesystem efêmero em free, incluindo perda de SQLite em reinício/redeploy/spin-down ([documentação](https://render.com/docs/free)). A configuração efetiva do painel não foi acessada.

Propor persistência comprovada antes de qualquer dado real; alternativa acadêmica sem novo serviço é apresentação local em máquina existente e backup. Migração planejada em `plano-migracao-banco.md`. Reteste: dado fictício sobrevive a reinício/redeploy e restore ensaiado; orçamento sem cobrança automática validado.

### SEC-11 — CI não atesta publicação — alta para prontidão

Evidência: `.github/workflows/ci.yml:39` contém apenas GET de `/login`, sem trigger explícito de Render, espera por commit, fingerprint ou verificação de banco. Run `35435187835` consta success no GitHub. Nesta rodada a URL conhecida `https://univet-frontend.onrender.com/login` respondeu **404**, embora o HTML tenha título UniVet. Não foi lido o valor privado de `PRODUCTION_BASE_URL`; pode ser outra URL.

Propor identificar backend correto, confirmar commit no painel/integração de deploy e health check versionado mínimo sem segredos. Reteste: identificar mesmo SHA no GitHub e Render, GET correto 200 e fluxos com dados fictícios em homologação. A auditoria não confirma qual versão está online.

### SEC-12 — PDFs enviados no histórico — violação confirmada da restrição de publicação

Evidência: `git ls-tree -r --name-only cf782ba -- output/pdf` lista quatro PDFs; `cf782ba` integra a ancestralidade do merge publicado `95d1369` e da tag `v2.0.0-pi2`. `9d28530` excluiu apenas a árvore atual; não os removeu dos commits anteriores. A afirmação anterior “PDFs não enviados” estava incorreta. Não foi necessário abrir o conteúdo para comprovar presença.

Os arquivos continuam locais e ignorados, mas isso não elimina cópias remotas antigas. Remediação proposta: planejar saneamento de todas as refs afetadas, preservar backup local, coordenar clones/caches e solicitar autorização específica para reescrever histórico remoto. Reteste: percorrer objetos alcançáveis de branches/tags; ausência apenas em `git ls-files` é insuficiente. Nenhuma reescrita foi executada nesta auditoria.

### SEC-13 — Histórico não atômico, concorrência de agenda e exclusão — alta/média

Evidência estática: `app.py:232`, `:1444`, `:1535`, `:1640`. Alteração principal é commitada antes do histórico em outra conexão; falha entre operações deixa evento ausente. Nova consulta busca maior ID em vez do ID do próprio INSERT, podendo atribuir histórico errado sob concorrência. Conflito de intervalo é checado antes de gravar; índice único de início não impede intervalos diferentes sobrepostos. Esses cenários de agenda não foram reproduzidos nesta rodada e permanecem riscos fundamentados no código.

Consulta usada pelo estoque tem FK RESTRICT em `itens_consulta`, porém a rota de excluir não trata esse erro. Prontuários permitem edição/exclusão sem política formal de adendo/fechamento. Propor transação única para evento+registro, `lastrowid`, proteção de conflito de agenda e recusa amigável da exclusão de consulta utilizada. Retestes concorrentes e falha injetada entre gravações; definir quais registros clínicos só recebem adendos.

### SEC-14 — Consumo não considera estornos — média; semântica a confirmar

Evidência: `estoque/services.py:499`, `:532`; consumo soma somente Saída, mesmo quando estornada; `itens_consulta` não é invalidado no estorno. Resultado pode ser intencional como consumo bruto, mas não deve ser apresentado como líquido sem definição. Propor distinguir consumo bruto/líquido e itens estornados; validar efeito na reposição e valores de atendimento. Reteste: uso, estorno e relatório preservam rastreabilidade e total escolhido. Não alterado automaticamente como preferência técnica.

### SEC-15 — Privacidade e continuidade sem procedimento comprovado — alta para clínica

Evidência: dados de tutores/CPF/endereço, nome em sessão assinada não criptografada, snapshots JSON em histórico (`app.py:232`), exportações com nomes e fontes Google em `templates/base.html:8` e `login.html:8`. Sem política documentada de retenção, revisão de acessos, cópia real e restauração periódica. Não implica vazamento confirmado.

Propor medidas em `privacidade-dados.md` e `runbook-producao.md`. Reteste operacional: acesso mínimo, logs sem dados pessoais, restauração com responsáveis, remoção/retenção coerente incluindo histórico e backups. Nenhuma conformidade jurídica é declarada.

## Proteções e limites observados

- Hash de senha via Werkzeug; SQL de entrada parametrizado e nomes dinâmicos de schema vindos de estruturas internas, não de input HTTP. Não foi encontrada interpolação de input nas consultas inspecionadas. Provas SQL pontuais não garantem ausência universal.
- Jinja escapa HTML por padrão; uso de `innerHTML` encontrado em formulário de pets contém literais; nomes de raças entram por `textContent`. Não encontrada aplicação de `|safe` nos templates pesquisados. Não houve teste de execução em navegador.
- Saídas e uso em consulta usam transação, lock, guard de quantidade e rollback; schema possui CHECK de saldo não negativo e FK. FEFO e rejeição de vencidos já possuem testes.
- APIs de estoque têm paginação limitada a 100; exportações/listagens auxiliares e consultas de dashboard não são integralmente limitadas. API anônima redireciona HTML em vez de JSON 401: melhorar contrato de integração. Sem CORS permissivo configurado observado.
- Busca de assinaturas comuns de tokens/chaves privadas no histórico local retornou zero; não é scanner de entropia completo nem certificação de ausência de segredos. Credenciais demo/fallback continuam achados separados. Não se imprimiram secrets de ambiente.
- `pip-audit` consultou os **12 pacotes do ambiente Python 3.11 correto**, sem vulnerabilidades conhecidas reportadas nesta consulta. Inclui bibliotecas locais de PDF, além da aplicação. Isso não garante dependências do deploy: `requirements.txt` usa intervalos e não fixa resolução. Primeira tentativa apontou diretório Python inexistente e foi descartada; só a segunda consulta com 12 pacotes fundamenta o resultado.
- Render declara Python 3.11.9 e Gunicorn 22; avaliar versões suportadas e travamento de dependências no próximo checkpoint, com teste de atualização. Caches de referência são por processo; dois workers podem divergir depois de cadastro/edição. Precisa teste multiprocesso específico.

## Evidências e encerramento

Artefatos locais ignorados: `artifacts/audit-local.json`, `audit-local.err`, `unittest.log`, `dependency-audit.json`, `dependency-audit.err`, `online-headers.txt`, `online-login.html`, `history-secret-signatures.log`, `codex-security-help.log`. Não publicar artefatos brutos automaticamente; compartilhe este resumo revisado.

Suíte completa: **27 testes passaram em 184,920 segundos**, exit 0, conforme `artifacts/unittest.log`; estado atualizado em `current-state.md`. Quatro skills validadas pelo `quick_validate.py`; script de reprodução compilou e `git diff --check` passou. Reproduções locais concluídas; nenhum teste ou código funcional legado foi alterado.

Codex Security: `npx @openai/codex-security --help` tentou iniciar, mas falhou com Node v18.19.1 incompatível com dependências do pacote. Nenhuma skill adicional foi sincronizada, nenhum scan remoto foi iniciado e nenhuma API paga foi usada. A documentação indica que scans dependem de acesso ao produto ([fonte oficial](https://learn.chatgpt.com/docs/security)); não pressupor disponibilidade gratuita. A auditoria manual/local seguiu normalmente.

Preparação de contexto: não havia AGENTS.md, `.agents/`, `.codex/`, `skills/` ou config.toml no repositório inspecionado. Preservada configuração de usuário; apenas quatro skills foram criadas. `skills.max_context_tokens` existe na [referência oficial](https://learn.chatgpt.com/docs/config-file/config-reference), mas nenhum valor foi aumentado nem imposto à versão instalada (`codex-cli 0.144.3`). Não se promete redução mensurável de tokens sem medir sessões comparáveis.

Próximas decisões: priorização em `checklist-producao-clinica.md`. Acesso ao painel Render e decisão de saneamento do histórico permanecem pendentes; não impedem concluir este relatório, mas impedem atestar produção e remoção remota dos PDFs.
## Atualização de continuidade — 22/09/2026

Esta etapa concluiu a validação local do caminho PostgreSQL sem tocar em produção:

- `DATABASE_URL`/`DEMO_DATABASE_URL` passaram a aceitar PostgreSQL com validação de esquema de URL, separação de ambientes e pool com limites conservadores.
- O baseline Alembic cria o schema PostgreSQL e registra o ambiente. Banco existente sem controle de migração é recusado; não há migração destrutiva automática nem seed demo em produção.
- Testes separados passaram: 14 HTTP e 24 de estoque/concorrência em PostgreSQL descartável local. A regressão SQLite pós-correção passou com 115 testes e 38 skips esperados. O run CI `35715647287` executou os grupos PostgreSQL em job separado e passou; `deploy` foi ignorado por a branch não ser `main`. O novo commit da correção ainda precisa concluir o próximo CI.
- Backup custom-format e restore em banco PostgreSQL vazio foram ensaiados com `pg_dump`/`pg_restore`; fingerprint de 22 tabelas coincidiu. O ensaio é apenas local, com dados fictícios.
- Foram corrigidas incompatibilidades de adaptação de data/timestamp e `last_insert_rowid()` no caminho de testes PostgreSQL. Não houve mudança deliberada de regra de negócio.

Isso reduz os bloqueadores de persistência/migração local e fecha a regressão de adaptação de timestamp, mas não fecha a auditoria de produção: ainda falta homologar um provedor persistente gratuito, HTTPS, deploy isolado, carga/soak final com identidades independentes, primeiro acesso operacional e confirmação de backup/restore no destino. O status permanece **NÃO APTO PARA DADOS REAIS**.
