---
name: univet-security-audit
description: Auditar defensivamente segurança do UniVet e avaliar exposição de dados, controles de acesso e riscos de produção; registrar achados sem corrigir a aplicação automaticamente.
---
# Processo de auditoria

Consulte contexto técnico apenas se necessário. Registre escopo, commit, evidência arquivo/linha, severidade, pré-condições, impacto, reprodução local, correção proposta e reteste em `docs/auditoria-seguranca.md`. Achados temporários não entram nesta skill. Não reproduza credenciais nem dados de clientes nos relatórios.
Mapeie rotas e decoradores: autenticação, hash, contas iniciais, limitação de tentativas, autorização por operação/registro, revogação após desativação. Não confunda perfis aceitos com controle por papel.
Verifique CSRF em todos os métodos mutáveis e login/logout, escape Jinja/DOM e XSS, consultas SQL parametrizadas e identificadores dinâmicos, sessão/chave/expiração, Secure/HttpOnly/SameSite, headers e cache de páginas privadas.
Revise APIs (auth, limites, erros, enumeração, CORS), CSV (fórmulas em células controladas pelo usuário), validações numéricas/finitude, transações e integridade de histórico. Use skill de testes para reproduções e concorrência.
Procure segredos no código e histórico com saída redigida; examine arquivos ignorados sem imprimir conteúdos sensíveis. Verifique dependências e advisories oficiais quando disponível; falha de scanner não significa ausência de vulnerabilidades.
Mapeie dados pessoais, logs, exportações, retenção e terceiros em `docs/privacidade-dados.md`. Não certifique conformidade jurídica a partir de inspeção técnica.
Produção: somente observação de baixa frequência sem login de demonstração ou mutações. Confronte CI, serviço real e commit; operação/backup na skill `univet-production-ops`. Sem evidência suficiente, marque não verificado, nunca aprovado por inferência.
