# Checklist de liberação — 22/09/2026

**NÃO APTO PARA DADOS REAIS.** [Auditoria](auditoria-seguranca.md) contém evidências e classificação. Marcado significa verificado localmente com dados fictícios, não implantado.

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
- [x] Backup e restore PostgreSQL local fictício com fingerprint de 22 tabelas.
- [x] 27 testes originais preservados; regressões novas incluídas.

## Bloqueadores e pendências obrigatórias

- [x] PostgreSQL completo local (conexão, SQL, migrações, testes, backup/restore); homologação remota ainda pendente.
- [ ] Confirmar Neon Free (ou alternativa) sem cartão, criar bancos Demo/Clínica independentes e URLs distintas.
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
