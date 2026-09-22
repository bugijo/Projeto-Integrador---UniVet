# Plano de persistência e migração — proposta, não implementada

## Atualização de execução — 21/09/2026

Docker disponível permitiu POC **isolada**, PostgreSQL 16 local sem volumes reais/serviço remoto: `perf/postgres_poc.py`. Cinco saídas concorrentes de 7 unidades contra saldo 10: uma aceita, saldo 3, um movimento, sem negativo. Artefato `artifacts/postgres-poc.log`, resultado explícito `application_migrated=false`. Contêiner descartável próprio encerrado pelo script.

Isso supera a limitação inicial de binários descrita abaixo, mas **não adapta a aplicação, não testa migração integral e não valida dump/restore PostgreSQL**. Conexão central agora em `config.py`, apenas URLs SQLite absolutas suportadas; URL PostgreSQL é recusada explicitamente. Produção SQLite no Render é bloqueada. SQLite em disco local existente exige declaração explícita e homologação operacional; não é aprovação automática.

Migração completa ainda PENDENTE: SQL parametrizado/dialeto, tipos/datas, transações/locks, schema versionado, dados fictícios íntegros, integração HTTP, restart e restore. Não usar tradutor genérico de SQL como substituto dos retestes. Nenhum provedor foi integrado/contratado. Condições gratuitas abaixo devem ser revalidadas antes da escolha; nenhuma cobrança autorizada.

## Pesquisa original preservada

Pesquisa documental em **19/09/2026** (America/Sao_Paulo). Base de código conferida: `95d1369`, branch `security/production-readiness`. Problema SEC-10 em `auditoria-seguranca.md`: SQLite local em filesystem efêmero não sustenta registros da clínica. A configuração efetiva do Render não foi inspecionada. O inventário abaixo representa a leitura inicial do código; havia trabalho paralelo no diretório, portanto deve ser reconferido antes da implementação.

Escopo desta revisão: somente este documento. Nenhuma conta, contratação, instalação, conexão a banco real, alteração de schema, migração pública, deploy ou commit. Neon e Aiven foram escolhidos para a comparação; Supabase não foi avaliado. As fontes são oficiais e os valores refletem a consulta, não uma garantia futura. Revalidar antes de qualquer integração.

## Persistência, custo e limites dos provedores

Valores em USD. “Grátis” refere-se ao plano e às cotas indicadas, não ao custo operacional da clínica. Todas as linhas foram verificadas em 19/09/2026; os links levam às fontes correspondentes.

| Opção | Custo e cartão | Armazenamento e cotas | Suspensão e duração | Backup e retenção | Compatibilidade e conclusão |
|---|---|---|---|---|---|
| Render Web Free + SQLite local | US$ 0; sem meio de pagamento, excesso provoca restrições; com pagamento, pode haver cobrança de excedentes. [Free](https://render.com/docs/free), [FAQ](https://render.com/docs/faq) | Filesystem efêmero; 750 h/mês por workspace. | Suspende após 15 min sem tráfego; despertar leva cerca de 1 min. Escritas locais somem ao suspender, reiniciar ou redeployar. | Arquivo SQLite local não é backup durável. | Executa Flask, mas não resolve persistência. |
| Render Postgres Free | US$ 0 durante a validade. [Limites oficiais](https://render.com/docs/free#free-postgres) | 1 GB; um banco gratuito por workspace; sem pool gerenciado. | Expira em 30 dias; fica inacessível, com mais 14 dias para upgrade antes da exclusão. | Sem backups fornecidos no Free; exportação externa necessária antes de expirar. | PostgreSQL compatível mediante adaptação Python; rejeitado como solução para o semestre. |
| Neon Free | US$ 0/mês, sem cartão; plano permanente, não trial. [Preços](https://neon.com/pricing) | 0,5 GB/projeto; 100 CU-h/projeto/mês; 5 GB de saída/projeto/mês; 100 projetos e 10 branches/projeto. [Planos](https://neon.com/docs/introduction/plans) | Computação suspende após 5 min ociosa. Esgotar computação ou tráfego suspende até próximo período; exceder armazenamento bloqueia operações que aumentem espaço. Esses limites não apagam dados. | Histórico de restauração de 6 h, limitado a 1 GB-mês de alterações segundo a documentação de planos. Um snapshot manual; sem snapshots agendados no Free. Exportação independente ainda necessária. [Histórico](https://neon.com/docs/introduction/plans#history-window) | Drivers Python usuais; pool PgBouncer disponível. Candidato preferencial para ensaio futuro pequeno e intermitente, condicionado às cotas. |
| Aiven for PostgreSQL Free | US$ 0, sem cartão e sem prazo de expiração. [Free tier](https://aiven.io/docs/products/postgresql/concepts/pg-free-tier) | 1 CPU, 1 GB RAM, 1 GB disco; nó único; 20 conexões; um serviço de cada tipo por organização; sem pool gerenciado, VPC ou SLA. | Pode desligar por falta de uso inicial nas primeiras horas ou inatividade continuada; esta recebe aviso prévio. Pode ser religado. Prazo exato de inatividade continuada não publicado nessa fonte. | Backups incluídos, mas **retenção do Free não explicitada** na [tabela de backups](https://aiven.io/docs/products/postgresql/concepts/pg-backups#backup-retention-time-by-plan); não atribuir ao Free os prazos de planos pagos. | [Conexão Python](https://aiven.io/docs/products/postgresql/howto/connect-python) documentada; alternativa com maior disco, condicionada a esclarecer recuperação e operar dentro de 20 conexões. |

Render oferece [discos persistentes somente em serviços pagos](https://render.com/docs/disks); só o caminho montado persiste. Essa alternativa fica fora da restrição de custo zero. Snapshots diários de disco não substituem backup consistente de banco.

A [FAQ do Render](https://render.com/docs/faq) contempla contas sem meio de pagamento, mas não garante ausência de verificação para toda conta. Uma [resposta do suporte no domínio oficial](https://community.render.com/t/the-deployement-of-a-web-service-fails/36005) informa que cartão pode ser solicitado para verificação (trecho indexado consultado; página completa indisponível nesta pesquisa). Não prometer cadastro universal sem cartão; se exigido, essa opção deixa de atender à restrição. Nenhum cadastro foi tentado.

O [Render Free](https://render.com/docs/free#service-initiated-traffic-threshold) também pode suspender tráfego externo iniciado pelo serviço considerado excessivo, inclusive para banco remoto. O limiar numérico não é publicado. Banco persistente externo não elimina essa limitação da aplicação.

No Neon, CU-h mede capacidade multiplicada por tempo ativo: 100 CU-h permitem 400 horas a 0,25 CU, não um mês inteiro sempre ligado. Computações adicionais do projeto compartilham a cota. O [pooler](https://neon.com/docs/connect/connection-pooling) aceita até 10.000 conexões de clientes, mas isso não equivale a 10.000 transações simultâneas; os limites efetivos dependem da computação. Usar conexão direta para migrações e dumps; o pool opera por transação e limita estado de sessão. A página de preços resume o histórico como “1 GB”; este plano adota a unidade mais explícita de **1 GB-mês** da documentação de planos. Não tratar esse histórico curto como retenção diária garantida nem presumir gratuidade/retenção de snapshot além do que o plano confirmar.

A documentação geral de [backup Aiven](https://aiven.io/docs/products/postgresql/concepts/pg-backups) descreve backup diário e envio de WAL em intervalos de 5 min ou a cada arquivo novo. A tabela de retenção não possui linha Free: inclusão de backup não comprova janela PITR nem restauração autônoma gratuita. Tráfego e comportamento exato ao lotar o disco também não têm cota numérica/regra explícita na página específica consultada; permanecem pendentes. Não assumir ausência de limites.

## Decisão proposta e alternativa sem serviço externo

Para demonstração com dados fictícios, priorizar avaliação futura do Neon se volume, atividade e exportações couberem nas cotas. Manter Aiven como alternativa, sobretudo pelo disco maior, após esclarecer retenção e recuperação. Nenhum provedor foi contratado ou homologado. Nenhum Free aqui comprova adequação a prontuários reais, disponibilidade contínua ou recuperação exigida pela clínica.

SQLite em máquina já disponível continua sendo a alternativa de menor mudança: software gratuito e armazenamento local persistente, com backup em outro meio já disponível. PostgreSQL local é alternativa de ensaio sem tarifa de provedor, quando os binários já existirem. Ambos exigem responsável pela máquina, recuperação e disponibilidade; não equivalem a nuvem sempre disponível. Não usar trial que expire durante o semestre.

## Compatibilidade Flask e inventário da migração

A skill local `univet-project-context` orientou o vínculo desta proposta à arquitetura. A leitura de `app.py`, `init_db.py`, `estoque/schema.py`, `estoque/services.py` e `requirements.txt` confirma SQL SQLite direto, sem ORM nem driver PostgreSQL declarado. Trocar apenas uma URL não migra o sistema. Os guias oficiais de [Python no Neon](https://neon.com/docs/guides/python) e [Python no Aiven](https://aiven.io/docs/products/postgresql/howto/connect-python) demonstram compatibilidade do protocolo com drivers Python; a aplicação UniVet ainda não foi testada nesses bancos.

Proposta futura: manter Flask/Jinja e centralizar conexão/configuração (hoje `DATABASE` é definido em dois módulos), com `DATABASE_URL` externa e segredo fora de logs e Git. Escolher e versionar um driver, por exemplo Psycopg 3, somente na etapa de implementação. Usar TLS com validação de certificado/hostname conforme provedor; `sslmode=require` sozinho não valida a identidade do servidor. Não criar conexão global compartilhada entre processos Gunicorn. Prever fechamento por requisição, rollback em exceções, timeout e limite total de conexões somando todos os workers e tarefas administrativas. No Aiven, reservar margem dentro das 20 conexões.

| SQLite/estado atual | Destino proposto e validação exigida |
|---|---|
| `INTEGER PRIMARY KEY AUTOINCREMENT` | `BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY`, preservando IDs existentes por inserção explícita e tipos iguais nas FKs. Não renumerar registros nem reutilizar IDs removidos. |
| IDs gerados com `lastrowid` | `INSERT ... RETURNING id`; capturar resultado na mesma operação, sem consultar `MAX(id)` para gerar IDs. |
| Valores monetários e quantidades `REAL` | Candidatos: dinheiro `NUMERIC(18,2)`, quantidade `NUMERIC(18,6)` e percentual `NUMERIC(9,4)`; confirmar amplitude e escala com o domínio antes de fixar. Usar `Decimal` de ponta a ponta; relatar diferenças de arredondamento e não alterar valores silenciosamente. |
| `ativo` inteiro 0/1 | `BOOLEAN` após inventariar valores e nulos; adaptar filtros `ativo = 1`, binds e serialização. Valores fora de 0/1 bloqueiam conversão automática. |
| Datas e horários `TEXT` | Validade em `DATE`; eventos e agenda em `TIMESTAMPTZ` somente após identificar origem/fuso. Há horários locais sem offset e defaults `CURRENT_TIMESTAMP` do SQLite; não aplicar cegamente um fuso único. Documentar conversão por campo para UTC e exibição em `America/Sao_Paulo`, incluindo datas históricas ambíguas. |
| CPF, telefone, códigos, hashes e textos clínicos | Continuar texto, preservando zeros, acentos, nulos e hashes sem rehash/reset. Conferir unicidade de CPF/login e distinguir vazio de `NULL`. |
| `historico_alteracoes.dados_json` e `registro_id` | Preservar JSON textual inicialmente para manter conteúdo auditável. JSONB seria mudança separada após validação; referências por `(entidade, registro_id)` exigem verificação lógica, não FK genérica. |
| `?`, `sqlite3.Row`, `sqlite3.IntegrityError` | [Parâmetros Psycopg](https://www.psycopg.org/psycopg3/docs/basic/params.html), row factory e exceções equivalentes; preservar acesso por nome/posição usado pelos consumidores. Valores sempre parametrizados. |
| `PRAGMA`, `sqlite_master`, `executescript`, triggers SQLite | Inventário e migrações PostgreSQL explícitas; reescrever introspecção e triggers de raça/espécie. Não executar `init_db.py` atual contra o destino. |
| `INSERT OR IGNORE`, `date()/datetime()`, `LIKE`, `ROUND` | Definir conflitos esperados em `ON CONFLICT`; converter datas/intervalos, conferir caixa/acentos nas buscas, ordem de nulos e arredondamento decimal. Não traduzir strings SQL mecanicamente. |
| `BEGIN IMMEDIATE` e operações de estoque | Transações PostgreSQL com bloqueio de linhas/atualização condicional, ordem estável de locks e tratamento de deadlock. Saldo, movimento, item e histórico devem confirmar ou reverter juntos. Não repetir escrita após timeout sem idempotência. |

Fundamentação dos tipos: [identity](https://www.postgresql.org/docs/current/ddl-identity-columns.html), [numéricos exatos](https://www.postgresql.org/docs/current/datatype-numeric.html) e [sequências](https://www.postgresql.org/docs/current/functions-sequence.html). As escalas acima são propostas do projeto, não exigências do provedor.

## Carga, IDs e integridade referencial

1. Inventariar o schema efetivo numa cópia privada consistente: tabelas, colunas adicionadas incrementalmente, índices, triggers, defaults, checks e FKs. Registrar versão/hash do código, tamanho e contagens sem publicar dados pessoais. Schema base não basta, pois `init_db.py` e `estoque/schema.py` acrescentam colunas.
2. Produzir snapshot SQLite com API de backup ou ferramenta equivalente consistente; não copiar isoladamente arquivo em uso com WAL. Verificar `integrity_check` e `foreign_key_check` na cópia. Medir também espaço esperado de índices e margem no destino; tamanho SQLite não estima diretamente uso PostgreSQL.
3. Separar migrações versionadas, bootstrap privado e seeds fictícios opt-in. Reexecução não pode apagar usuários, redefinir senhas ou duplicar dados. Criar schema de destino vazio para o ensaio, sem carga de demonstração automática.
4. Carregar pais antes dos filhos: usuários, tutores, espécies (pais antes dos descendentes), veterinários, serviços, categorias e fornecedores; depois raças/produtos; pets/lotes; consultas/condições clínicas; movimentações; itens de consulta. Histórico requer conferência lógica final. Resolver a autorreferência `movimentacao_origem_id` em segunda passagem ou por constraints diferíveis deliberadas; tratar `especies.parent_id` e detectar ciclos.
5. Preservar IDs e regras `ON DELETE` existentes, inclusive `RESTRICT`, `SET NULL` e `CASCADE`. Colunas incrementais como `pets.especie_id`, `pets.raca_id`, `consultas.servico_id` e `consultas.veterinario_id` não recebem FK na declaração atual: verificar órfãos e incoerências antes de adicionar constraints. Não descartar registros para fazer a carga passar. FKs/checks devem estar validados ao concluir, sem desativação permanente de integridade.
6. Reajustar cada sequência após carga, considerando tanto `MAX(id)` quanto a marca histórica de `sqlite_sequence` para evitar reutilizar IDs apagados. Para tabela nunca populada, próximo ID deve ser 1; para as demais, maior marca + 1, respeitando limite do tipo. Validar inserção automática posterior. `setval` não é desfeito por rollback: registrar a marca e recalcular ao repetir uma carga interrompida; não assumir sequência sem lacunas.
7. Registrar mapeamento identidade→identidade e exceções recusadas. Implantar antes do corte as invariantes pendentes: estorno único, ajuste atômico, histórico junto da operação e agenda sem sobreposição. PostgreSQL não corrige essas falhas automaticamente.

## Validação e POC local condicional

**Resultado desta etapa:** pesquisa e revisão estática apenas. `command -v` não encontrou `psql`, `postgres`, `initdb`, `pg_ctl`, `pg_dump` ou `pg_restore`; `/usr/lib/postgresql` e `/usr/local/pgsql/bin` estavam ausentes. Não houve instalação nem procura/conexão a serviços remotos. POC PostgreSQL **não executada** por ausência de binários nos locais verificados; não há evidência de migração ou restauração PostgreSQL aprovada. Esta alteração documental não executou a suíte da aplicação.

Se os binários já estiverem disponíveis em etapa posterior, a POC deve usar cluster temporário isolado, socket local privado, porta não conflitante e somente dados fictícios. Não iniciar serviço do sistema nem reutilizar um banco existente. O escopo desta revisão não inclui criar scripts ou alterar outros arquivos para isso.

Critérios para considerar o ensaio aprovado:

- Igualdade de contagens e conjuntos de PKs por tabela; comparação de conteúdo normalizado por chave (decimais/datas), não apenas total de linhas. Zero órfãos e zero violações de constraints; preservar vínculos, hashes, prontuários e histórico. Divergências de dados legados bloqueiam aceite até decisão registrada.
- Totais monetários e quantidades por produto/lote conferidos. Conciliar saldo com movimentos assinados e saldo de abertura efetivamente representado, sem contar entrada inicial duas vezes. Conferir FEFO, lotes vencidos, nulos e ajustes/estornos anteriores; tolerâncias só para conversões previamente aprovadas.
- Próximos IDs corretos, inclusive tabelas vazias e maior ID histórico removido; testes de unicidade, referências de raça/espécie, autorreferências e políticas de exclusão.
- Testes funcionais de login, CRUD, agenda, consultas e estoque; suíte existente adaptada ao PostgreSQL. Casos concorrentes de saída/ajuste/estorno e agendamento devem manter saldo não negativo, estorno único e ausência de sobreposição. Injetar erro para comprovar rollback integral de cada operação.
- Interromper e repetir a carga sem duplicação; reiniciar cluster e confirmar persistência. Testar desconexão, limite de pool e retomada sem duplicar gravações. Reinício local não comprova comportamento no Render; eventual teste de redeploy remoto exigirá etapa futura própria, com dados fictícios.
- Gerar [dump PostgreSQL](https://www.postgresql.org/docs/current/backup-dump.html), restaurar em segundo banco vazio e repetir comparações. Registrar versões, hash do backup, duração de carga/restauração e resultado. Ter dump sem restauração testada não satisfaz o critério.

## Corte futuro, backups e rollback

Execução pública não faz parte desta tarefa. Antes de propor um corte real, definir responsável, volume, janela de manutenção, RPO (perda máxima), RTO (tempo de recuperação), destino externo de backups e retenção aprovada. Proposta para ensaio: exportação antes/depois da carga e diária enquanto houver alterações, mantendo sete cópias diárias em meio separado já disponível; isso é política proposta, não recurso garantido pelo Free. Dados clínicos exigem acesso restrito e backup protegido. Exportações também consomem a cota de tráfego do provedor.

1. Suspender todas as escritas e jobs, registrar instante de corte, versão da aplicação e schema. Gerar backup SQLite consistente, conferir hash e restauração isolada. Preservar original e código anterior durante toda a janela de reversão.
2. Carregar o PostgreSQL sem liberar usuários. Conferir os critérios acima e um teste de leitura/escrita fictícia controlada. Só liberar após aceite registrado; qualquer divergência inexplicada, falha de integridade, restauração ou cota impede abertura.
3. **Falha antes de novas gravações reais:** descartar logicamente o destino do ensaio, restaurar a versão anterior e apontar para a cópia SQLite íntegra em ambiente persistente disponível. Validar e reabrir. Voltar ao SQLite no disco efêmero do Render não restaura durabilidade.
4. **Falha depois de novas gravações:** congelar novamente, preservar PostgreSQL e exportar estado final. Não basta trocar a URL ou restaurar o SQLite antigo. Exigir migração reversa ensaiada que preserve IDs, inserts, updates, exclusões, movimentos e histórico, seguida de reconciliação integral; alternativamente, corrigir o destino e manter os dados. Sem caminho reverso validado, permanecer em manutenção. Não prometer rollback sem perda nessa condição.
5. Documentar dados de origem/destino autoritativos, instante final, diferenças, responsável e liberação. Nunca operar duas bases aceitando escrita simultânea durante o retorno. Reter backups pré/pós-corte pelo prazo acordado; exclusão posterior requer procedimento próprio.

Pendentes para implementação: provedor final; requisitos clínicos e de privacidade; volume/crescimento; semântica de fuso/precisão; retenção e restauração Aiven Free; cotas aplicáveis à conta Render; driver e adaptação SQL; binários para POC; responsáveis e RPO/RTO. Nenhuma escolha documental autoriza contratação, cobrança ou migração pública.
## Atualização — 22/09/2026

Desde a pesquisa inicial registrada abaixo, o ambiente local passou a usar um PostgreSQL descartável em Docker somente para validação. O baseline Alembic foi aplicado, os testes PostgreSQL separados passaram (13 HTTP e 24 estoque/concorrência) e um backup/restore custom-format foi validado por fingerprint de 22 tabelas. Nenhum provedor remoto, produção ou dado real foi acessado. A conclusão de homologação externa permanece pendente.
