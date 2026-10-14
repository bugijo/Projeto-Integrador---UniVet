# Checklist de liberação — 28/09/2026

## Escopo da rodada acadêmica — 13/10/2026

- [ ] Serviço online demo gratuito validado sem cobrança, cartão ou plano pago.
- [ ] PostgreSQL demo separado confirmado com migrations, persistência e dados exclusivamente fictícios.
- [ ] Fluxo acadêmico completo validado no endereço público.
- [ ] Nenhuma conta `DrFernanda` criada enquanto houver bloqueadores.

## Checkpoint atual — 13/10/2026

- [x] `main` consolidada por merge explícito no commit `b1eda26`; branch Security preservada.
- [x] Pós-merge: 119 testes locais sem falhas e 38 testes PostgreSQL opt-in sem falhas.
- [x] `git diff --check`, `compileall` e smoke local Gunicorn concluídos.
- [x] Render inspecionado sem expor valores de secrets.
- [ ] Render operacional: workspace suspenso por não pagamento; URLs Demo e Clínica retornam 503.
- [ ] Deploy de `b1eda26` no Render.
- [ ] Revalidar Neon, `SELECT 1`, migrations, persistência, restart/redeploy e isolamento após o serviço voltar a operar.
- [ ] Criar `DrFernanda` somente depois de zero bloqueadores; não criada nesta rodada.

**Classificação atual: NÃO APTO PARA DADOS REAIS / NÃO APTO PARA PILOTO CONTROLADO.**

**NÃO APTO PARA DADOS REAIS.** [Auditoria](auditoria-seguranca.md) contém evidências e classificação. O serviço clínico agora responde 200, mas a homologação de continuidade, isolamento e carga ainda está pendente.

## Checkpoint remoto

- [x] Render `univet-clinica` live com psycopg 3.3.6/libpq 18.6.
- [x] Neon conectado com `verify-full`, CA confiável e `channel_binding=require`.
- [x] `/health`, `/login` e `/` retornando 200; headers e cookie seguro observados.
- [x] Suíte PostgreSQL local: 38 testes, 74 subtestes, 0 falhas.
- [x] `pip-audit`: nenhum advisory conhecido.
- [ ] Confirmar `alembic_version` diretamente no Neon.
- [ ] Criar dados fictícios e validar fluxo remoto completo.

## Controles locais

- [x] Seed demo opt-in; banco novo de produção sem contas/pacientes/produtos fictícios.
- [x] Configuração central e ausência de fallback demo → produção.
- [x] Marca do ambiente no banco e assinatura/cookie isolados.
- [x] Segredo obrigatório, DEBUG off, HTTPS/Secure/HSTS em testes.
- [x] CSRF, sessão revogável, autorização admin/veterinária, API/CSV protegidos.
- [x] Senha temporária aleatória por CLI, troca obrigatória e revogação.
- [x] Saídas/FEFO/ajustes/estornos concorrentes e rollback.
- [x] Agenda concorrente e histórico de cadastros na mesma transação.
- [x] Consultas canceladas sem exclusão; proteção de concluídas/condições/autoria.
- [x] Backup E restore SQLite fictícios comparando conteúdo.
- [x] PostgreSQL remoto Neon Free criado em projetos separados; migrations aplicadas e isolamento inicial verificado.
- [x] Backup PostgreSQL remoto gerado em formato custom, sem expor credenciais.
- [x] Restore do backup remoto em banco separado aprovado: 22 tabelas, 28 FKs, Alembic `002_session_indexes` e fingerprints equivalentes.
- [x] 27 testes originais preservados; regressões novas incluídas.

## Bloqueadores e pendências obrigatórias

- [x] PostgreSQL completo local e migrations remotas; backup/restore remoto ensaiado em projeto separado.
- [x] Neon Free confirmado e bancos Demo/Clínica independentes criados; ausência de cobrança automática ainda requer confirmação operacional.
- [ ] Criar/homologar serviço Clínica isolado sem substituir o Demo.
- [ ] Homologar persistência em restart E redeploy do alvo.
- [ ] Backup fora da instância, agendamento, responsável, retenção/RPO/RTO e restore do alvo.
- [ ] Confirmar HTTPS/secrets/SHA/configuração efetiva dos dois serviços.
- [ ] Corrigir ou explicar timeout no soak e repetir carga da versão final.
- [ ] Concluir política de adendos/edições clínicas, constraints legadas e caches multiprocesso.
- [ ] Precisão financeira e efeito de estornos em consumo/reposição/itens.
- [ ] Validar fluxo clínico completo na arquitetura final.
- [ ] Nomear responsáveis por acesso, dados, incidente e piloto.
- [ ] Resolver publicação de PDFs ancestrais com autorização própria.
- [ ] Revisão final independente e aprovação antes de criar DrFernanda.

## Liberação

Somente após zero bloqueadores: **APTO PARA PILOTO CONTROLADO**, não segurança absoluta nem operação regular automática. Não alterar serviço demo atual, introduzir dados reais ou gerar senha da veterinária antes disso.
