---
name: univet-production-readiness
description: Auditar segurança, privacidade, banco, backup, recuperação, concorrência, carga e prontidão do UniVet antes de permitir uso com dados reais.
---
# Prontidão para clínica

Orquestre as skills locais existentes, sem duplicar seus checklists: `univet-project-context` para arquitetura, `univet-security-audit` para controles, `univet-testing` para provas isoladas e `univet-production-ops` para recuperação/publicação.
Trabalhe em branch própria, registre commit-base e execute testes antes e depois. Use apenas dados fictícios; nunca testes destrutivos, exploração ou carga em produção. Não migre banco público nem altere conta real durante auditoria.
Mapeie rotas e revise autenticação, autorização/IDOR, CSRF/XSS/SQL injection, sessões/cookies, APIs/CSV, segredos e privacidade. Confirme persistência, backup E restauração, integridade, concorrência de estoque/agenda e carga local com métricas. Consulte --help/schema antes de scanners; não execute scans pagos sem autorização e custo conhecido.
Correções reversíveis autorizadas exigem regressões; preserve evidências antes/depois em `docs/auditoria-seguranca.md`, estado curto em `docs/current-state.md` e logs redigidos fora do Git.
Classifique riscos: BLOQUEADOR, ALTO, MÉDIO, BAIXO, INFORMATIVO. Não liberar dados reais com bloqueadores. Piloto exige persistência, restore, HTTPS, contas individuais, CSRF, autorização, estoque consistente e testes verdes; operação exige também piloto concluído, responsáveis e recuperação comprovada.
