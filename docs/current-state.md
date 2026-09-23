# Estado atual — 23/09/2026

## Homologação remota parcial — Neon Free — 23/09/2026

- A conta/organização Neon foi confirmada pela CLI oficial no plano **Free**. A API de limite de gastos não está disponível nesse plano; não houve upgrade, cartão cadastrado por esta tarefa ou recurso pago criado.
- Foram criados dois projetos PostgreSQL independentes, ambos sem dados reais: `univet-demo` (`winter-resonance-45187411`) e `univet-clinica` (`bold-truth-16986362`).
- Conexões remotas foram validadas com SSL `verify-full` e CA do sistema. Migrations Alembic concluídas nos dois bancos.
- Demo recebeu somente seed fictício. Verificação: `usuarios=2`, `tutores=5`, `pets=8`, `consultas=4`, `produtos=5`, `lotes=7`, `movimentacoes_estoque=10`.
- Clínica recebeu apenas o schema e dados estruturais de referência; os contadores de negócio verificados estão zerados. Não houve seed demo nem importação real.
- `pg_dump` remoto foi gerado com cliente PostgreSQL 17 em container descartável. O restore em banco de teste separado ainda não foi aprovado devido a incompatibilidades/instabilidade do ensaio descartável; não declarar backup/restore operacional até repetir com evidência limpa.
- O MCP Neon não está exposto como ferramenta nesta sessão do Codex; a CLI oficial autenticada foi o fallback. Nenhum token foi colocado no Git, na documentação ou no chat.
- Nenhum segundo serviço Render foi criado. O serviço Demo existente permaneceu inalterado; a criação de um serviço clínico Free foi bloqueada preventivamente pelos riscos de cobrança suplementar, suspensão e ausência de persistência adequada do plano Free.
- **Classificação: NÃO APTO PARA DADOS REAIS.** Persistem bloqueadores de serviço clínico isolado, headers/HTTPS efetivos, restart/redeploy, backup/restore, fluxo remoto, carga e revisão operacional.

## Atualização da validação PostgreSQL e carga local — 22/09/2026

- A regressão identificada no primeiro teste de carga PostgreSQL foi corrigida no adaptador de linhas: timestamps `datetime` retornam novamente a precisão de minuto esperada pelas rotas legadas. A regressão de agenda foi adicionada a `tests/test_postgres.py`.
- Pós-correção: **14 testes HTTP PostgreSQL OK** em 82,301 s; regressão SQLite **115 testes OK, 38 ignorados**, em 20,312 s. Os 38 ignorados são os grupos PostgreSQL opt-in quando a suíte roda sem `UNIVET_TEST_POSTGRES=1`.
- A nova carga local descartável, com Gunicorn/2 workers e dados fictícios, teve 0 falhas nos perfis de 1 e 5 usuários. Nos perfis de 10–50 e no soak de 10 usuários/120 s, as falhas foram exclusivamente `POST /login` recusados pelo limite de segurança de 10 tentativas por conta em 15 minutos, porque todos os usuários virtuais reutilizaram a mesma conta `admin`. Isso não é aprovado como teste de capacidade autenticada; o limitador não será desativado e a medição precisa ser repetida com contas fictícias independentes.
- A carga continua pendente para aprovação: não houve execução remota, nem soak de 10–20 minutos com identidades independentes. A falha funcional de timestamp está fechada localmente; a estabilidade operacional continua aberta.

## Atualização desta etapa — PostgreSQL, migração e continuidade

- O suporte PostgreSQL foi implementado localmente com `DATABASE_URL`, adaptador psycopg, pool limitado e migrações Alembic versionadas. A migração cria o schema completo sem seeds de demonstração; o ambiente é gravado e validado no banco.
- Dependências instaladas no `.venv`: `psycopg[binary,pool]` e `alembic`, com intervalos compatíveis. Nenhuma dependência paga foi adicionada.
- Validação SQLite regressiva: **114 testes OK, 37 ignorados**, 18,863 s, sem alteração funcional observada. Log: `artifacts/sqlite-regression-after-pg-adapter.log`.
- Validação PostgreSQL em containers descartáveis locais, criada exclusivamente para os testes: **13 testes HTTP OK** (`artifacts/postgres-http-final.log`) e **24 testes de estoque/concorrência OK** (`artifacts/postgres-stock-concurrency-final.log`). A execução agregada foi separada porque o runner acumulou tempo/limpeza de containers; isso não substitui uma execução CI limpa.
- Backup/restore PostgreSQL local validado com `pg_dump`/`pg_restore` em formato custom, banco de destino vazio e comparação de fingerprint de **22 tabelas**. O ensaio usou somente dados fictícios e container descartável; ainda não valida provedor externo.
- A limitação de compatibilidade entre SQL legado SQLite e PostgreSQL ficou encapsulada no adaptador; rotas, regras FEFO, estoque, histórico e agenda não foram redesenhados nesta etapa.

- Branch: `security/demo-producao-isolados`, criada de `chore/contexto-auditoria-producao` conforme novo roteiro. Base pública `95d1369`; confirmar HEAD/status no Git. Sem push, deploy ou alteração de dados reais.
- **NÃO APTO PARA DADOS REAIS. Tarefa ampla ainda não concluída.** Critérios e pendências em `prontidao-clinica.md`; auditoria inicial preservada como histórico, atualização no topo de `auditoria-seguranca.md` prevalece.
- Commits locais: `7531f4d` concorrência; `ee20d1f` segurança HTTP/agenda; `3368d38` backup; `6a50dde` validações; `9718c20` isolamento/primeiro acesso; `0124788` histórico atômico/preservação clínica.
- Testes anteriores: 77/77 em 18,673 s = 27 originais +50 novos, incluindo primeiro acesso HTTPS/restart em produção fictícia. A regressão atual SQLite é registrada no checkpoint acima; bancos descartáveis, nunca `banco.db`.
- Ambiente: `config.py`, DEMO_DATABASE_URL/DATABASE_URL independentes, marca persistente do ambiente, cookies/salt distintos. URLs SQLite absolutas e PostgreSQL suportados localmente; produção SQLite exige declaração de disco local persistente e é recusada no Render. O provedor recomendado está documentado em `docs/provedor-postgresql.md`, mas ainda não foi contratado/configurado.
- Conta: CLI gera senha temporária aleatória apenas em TTY, hash Werkzeug, troca obrigatória, revogação/rotação; primeiro acesso redireciona dashboard após troca. DrFernanda **não criada** e nenhuma senha dela gerada.
- Proteções verificadas: CSRF, RBAC server-side, API/CSV, sessão, headers, limites, FEFO/transações, estorno/ajuste/agenda concorrentes; restore SQLite fictício integral. Consultas canceladas sem exclusão; concluídas protegidas. Política formal de adendos ainda pendente.
- Carga anterior: seis perfis 1–50 sem erros; soak 600 s = 1 timeout/37.680, integridade ok. Não aprovar estabilidade plena; resultados são de snapshot anterior às mudanças PostgreSQL. Ver `relatorio-carga.md`.
- Ferramentas: `pip-audit` em ambiente temporário após as dependências atuais: **0 vulnerabilidades conhecidas**. Bandit atual: 4 médios/22 baixos, sem altos; os médios são bind local, identificadores SQL internos e subprocessos controlados de testes, registrados para revisão. Codex Security 0.1.29 executa com Node22 temporário, somente dry-run antes/depois, autenticação não verificada; sem scan pago. PostgreSQL local migrado e testado em containers descartáveis; ainda não é homologação externa.
- CI: o workflow agora executa a regressão SQLite e um job PostgreSQL opt-in em containers descartáveis, separado por classes HTTP e estoque/concorrência. O run `35715470083` do commit `251bcdf` passou nos jobs `test` e `postgres`; `deploy` foi ignorado fora da `main`.
- Render somente leitura: serviço `univet`, plano Free, branch `main`, URL `https://univet.onrender.com`, deploy live no commit `95d1369`; não é a clínica homologada. Não há PostgreSQL Render provisionado. A URL responde HTTPS, mas a resposta observada não apresentou os headers de segurança esperados; o serviço não foi alterado.
- Próximos passos locais: ação humana para criar dois projetos PostgreSQL gratuitos e um segundo serviço Render isolado; depois executar homologação remota, restart/redeploy, backup/restore e carga final. Corrigir/decidir lacunas SEC-09/13/14. Não refazer achados já corrigidos sem mudança relevante.
- Dependências externas: identificar backend/URLs/SHA, escolher persistência gratuita sem cartão/cobrança, validar restart/redeploy/backup do alvo e responsáveis. Não alterar produção sem confirmação. PDFs no histórico remoto (SEC-12) exigem autorização específica para saneamento.
- Artefatos brutos em `artifacts/` e `perf/results/`, ignorados. Não executar `docs/audit_local.py`: reprodução histórica das falhas antigas; usar regressões atuais.
