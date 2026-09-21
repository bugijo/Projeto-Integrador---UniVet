---
name: univet-production-ops
description: Planejar ou executar publicação, diagnóstico do Render, backup, restore, rollback e resposta a incidentes do UniVet conforme autorização vigente.
---
# Operação

Para arquitetura leia `univet-project-context` quando necessário. Use `docs/runbook-producao.md` para procedimentos/evidências e `docs/checklist-producao-clinica.md` para pendências; confirme estado real antes de executar. Auditar não autoriza publicar, alterar usuários ou migrar banco.
GitHub: status/diff, branch própria, suíte completa, revisão, backup do commit anterior, merge sem force push; verificar CI e conteúdo de TODOS os commits enviados (arquivos removidos continuam no histórico).
Render: confirmar serviço, branch, build/start, variáveis por NOME e commit ativo sem exibir valores. Job GitHub chamado deploy pode ser somente smoke. Verificar persistência do banco e condições atuais do free tier antes de aprovar clínica; não adicionar cartão/serviço pago. Separar demonstração de operação real.
Banco: jamais executar `init_db.py` em produção sem resolver reset/exclusão de usuários e seeds. Provisionamento inicial seguro requer comando separado, senha privada, sem dados demo; se inexistente, registrar bloqueio em vez de improvisar acesso.
Backup SQLite: usar API `sqlite3.Connection.backup` para destino restrito fora de Git, verificar integrity_check e foreign_key_check na cópia, registrar data/hash sem dados pessoais. Validar restore em diretório isolado antes de trocar banco. Para banco remoto, confirmar acesso e armazenamento persistente antes de prometer backup.
Rollback: preservar backup de código E dados; conferir compatibilidade do schema. Reverter por commit/redeploy autorizado, sem reset destrutivo ou restauração que perca registros sem decisão explícita.
Incidente: conter exposição, preservar evidências restritas, identificar commit/intervalo afetado, revogar sessões e trocar segredos se autorizado, recuperar cópia validada, retestar e documentar. Não publicar informações pessoais ou credenciais no GitHub.
