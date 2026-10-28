# Manutenção segura de produtos e lotes — Plano

> Execução nativa nesta sessão; plano baseado no pedido de manutenção de estoque de 28/10/2026.

**Objetivo:** Permitir excluir produto/lote somente quando não houver rastreabilidade vinculada, editar dados cadastrais de lote sem alterar saldo e proteger as operações por confirmação, CSRF e autorização administrativa.

**Arquitetura:** Regras de existência de histórico ficam em `estoque/services.py`; rotas POST transacionais em `app.py` consultam novamente os vínculos antes de alterar. Jinja mostra disponibilidade e bloqueios; edição cadastral de lote nunca grava entrada/saída. Sem migration ou cascade.

**Stack:** Flask, SQLite e PostgreSQL já suportados, Jinja2, `unittest`.

**Escopo:** Exclusão física só quando não há referências; produto com lote/movimento/item de consulta fica preservado e pode ser desativado. Lote requer ausência de movimento/item de consulta e saldo atual zero para exclusão. Produto do lote só muda sem histórico; código/validade/fornecedor são campos cadastrais separados do saldo.

## Arquivos

- `estoque/services.py`: helpers de histórico e indicadores para listagens.
- `app.py`, `security.py`: editar/excluir lote, excluir produto, lock transacional e escrita admin.
- `templates/estoque/produtos/{lista,detalhe}.html`, `templates/estoque/lotes/{lista,edicao}.html`: ações, confirmação e razões de bloqueio.
- `tests/test_stock_maintenance.py`: regressões SQLite isolado para histórico, confirmação, CSRF, autorização, edição, exclusão e ajuste.
- `docs/regressao-academica-2026-10-27.md`, `docs/current-state.md`: regras e evidência da rodada.

## Etapas testáveis

1. Escrever testes que falhem para excluir produto vazio; bloquear produto com lote, movimentação ou item de consulta; exigir confirmação/CSRF/admin; permitir excluir lote sem histórico e saldo zero; bloquear lote histórico/com saldo; permitir trocar produto somente sem histórico; demonstrar edição cadastral sem movimentação e ajuste com movimentação.
2. Implementar consultas/helper e rotas POST/GET mínimas; rodar testes focados.
3. Implementar formulários e ações Jinja; validar mensagens e acessibilidade.
4. Rodar suíte SQLite completa, suíte PostgreSQL opt-in, `compileall` e `git diff --check`; auditar candidatos fictícios no SQLite publicado sem excluir nada e registrar relatório de elegibilidade.
5. Fazer backup validado do banco publicado; commit/push `main`, fast-forward no PythonAnywhere, reload e smoke funcional com dados fictícios temporários; retirar apenas registros temporários criados nesta homologação quando elegíveis pelas novas regras.

## Revisão de cobertura

- Histórico de entrada/saída/ajuste/estorno é coberto por `movimentacoes_estoque`; consumo em consulta também é conferido em `itens_consulta` diretamente.
- FKs `ON DELETE RESTRICT` permanecem como última barreira; não se adiciona `CASCADE` nem se altera schema.
- Rotas mutáveis permanecem POST, CSRF global e admin-only; GET não exclui.
- Nenhum candidato remoto será removido sem relatório de referências e saldo; histórico existente será mantido.
