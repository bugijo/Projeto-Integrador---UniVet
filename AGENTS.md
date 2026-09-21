# UniVet

Projeto acadêmico PI II: Python/Flask, SQLite, Jinja2, CSS e JavaScript nativos.
Leia primeiro `docs/current-state.md`; confirme branch/commit com Git.

- Instalação: `.venv/bin/python -m pip install -r requirements.txt`.
- Execução local: `.venv/bin/python app.py`. Inicialização de banco: consulte a skill de operação antes de executar `init_db.py` sobre banco existente.
- Testes em `tests/`: `.venv/bin/python -m unittest discover -s tests -v`.
- `main` é publicação; trabalhe em branch própria. Histórico: `feature/integracao-propostas-estoque`, tag `v2.0.0-pi2`.
- Use somente dados fictícios em testes; não execute carga agressiva em produção.
- Use ferramentas gratuitas/open source; antes de integrar serviço externo, informe finalidade, limites gratuitos e alternativa sem custo. Sem cobrança automática ou cartão obrigatório.
- Testes direcionados durante correções; suíte completa antes de commit importante, merge, deploy e conclusão de auditoria. Economia de contexto nunca reduz segurança ou testes necessários.
- Skills específicas em `.agents/skills/`: `univet-project-context` (arquitetura), `univet-security-audit` (auditoria), `univet-testing` (verificação), `univet-production-ops` (operação). Carregue somente as relevantes.
- Localize com `rg`/`git grep` antes de ler trechos; reutilize leituras de arquivos inalterados e `git diff`. Verifique documentos equivalentes antes de criar novos.
- Registre decisões/resultados nos documentos da tarefa e atualize `docs/current-state.md` nos checkpoints. Logs extensos em `artifacts/` ou `docs/audit-artifacts/`; exponha apenas resumo/erros, sem segredos ou dados pessoais.
- PDFs em `output/pdf/` são locais e não devem ser publicados, inclusive por commits ancestrais.
