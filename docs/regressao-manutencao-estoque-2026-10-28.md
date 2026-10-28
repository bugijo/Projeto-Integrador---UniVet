# Regressão — manutenção segura de produtos e lotes

Data: 28/10/2026. Ambiente acadêmico PythonAnywhere Free, SQLite persistente, apenas registros fictícios. Nenhum seed foi reaplicado e nenhum registro online foi alterado/excluído nesta etapa.

## Regras implementadas

- Produto sem lotes, movimentos ou itens de consulta: exclusão somente por POST, com confirmação, CSRF, sessão autenticada e autorização de administrador.
- Produto referenciado por qualquer lote, movimentação ou item de consulta: exclusão física bloqueada; desativar continua disponível para preservar rastreabilidade.
- Lote sem movimentos/itens de consulta e com saldo zero: pode ser excluído via POST confirmado. Qualquer histórico ou saldo diferente de zero bloqueia a exclusão.
- Troca do produto associado ao lote só é aceita sem histórico. Código, validade e fornecedor são dados cadastrais; ajuste de quantidade permanece operação separada e gera movimentação auditada.
- As regras são reavaliadas dentro da transação de escrita. Foreign keys restritivas seguem como proteção adicional; sem cascade ou migration.

## Testes locais

- `TMPDIR=/dev/shm PYTHONPYCACHEPREFIX=/dev/shm/univet-stock-pycache PYTHONPATH=tests .venv/bin/python -m unittest test_stock_maintenance -v`: 13 testes aprovados.
- Cópia de trabalho temporária segura em `/tmp` (sem `.venv`, `.git` ou artefatos de performance; alterações versionadas e quatro arquivos novos preservados): suíte SQLite completa, 148 testes, 0 falhas/erros, 38 skips PostgreSQL opt-in. Os três testes de subprocesso WSGI/app que antes expiraram passaram isoladamente e na suíte completa.
- PostgreSQL opt-in executado com Docker em ambiente limpo: 38 testes, 0 falhas/erros, em 162,6 s. Inclui FEFO, saídas, estoque, consultas com baixa, HTTP/CSV e concorrência com 2/5/10 conexões. As falhas anteriores (`PoolTimeout` e Docker stop/start timeout) não se reproduziram nesta execução; eram transitórias de infraestrutura/container, não regressão confirmada.
- Volume NTFS teve períodos de leitura bloqueada: mount RW, 40% de espaço e 1% de inodes usados, porém `mount.ntfs` permaneceu em estado D e comandos Git simples também aguardaram I/O. A execução na cópia temporária contornou o bloqueio sem tocar no clone oficial; ao fim, o clone voltou a responder. `compileall` e `git diff --check` no clone oficial concluíram com sucesso.

## Auditoria prévia do banco demo online

Backup criado antes da auditoria: `/home/Bugijo/univet-demo-pre-audit-20261028-145234.sqlite3`, permissão restrita, `PRAGMA integrity_check = ok`, `PRAGMA foreign_key_check` com zero linhas.

| Registro QA fictício | Ativo | Lotes | Movimentações do produto | Itens de consulta | Decisão |
| --- | ---: | ---: | ---: | ---: | --- |
| `QA acadêmico 20261027-c03279 Produto A` (id 10) | Não | 3 | 5 | 0 | Preservar; não elegível |
| `QA acadêmico 20261027-afeb13 Produto A` (id 11) | Não | 3 | 7 | 1 | Preservar; não elegível |
| `QA acadêmico 20261027-afeb13 Produto B` (id 12) | Não | 1 | 3 | 1 | Preservar; não elegível |

Os sete lotes identificados (ids 12–18; QA-1, QA-2, QA-3 e QA-B) têm movimentações; os lotes 16 e 18 também têm referência de consulta. Saldos incluem zero e valores positivos. Nenhum lote foi excluído, reatribuído ou editado: não há lote sem histórico no conjunto auditado. Os produtos já estavam desativados. Não houve limpeza, seed, escrita no banco ou alteração de dados da demonstração.

## Limites e publicação

- As 13 regressões novas exercitam SQLite isolado: confirmação, GET sem mutação, CSRF/admin, produto com lote/movimento/consulta, desativação, edição e exclusão de lote, troca segura de produto, saldo e separação entre cadastro e ajuste.
- Regressões novas: 13/13 passaram. Revisão independente read-only: sem achados bloqueadores.
- `PYTHONPYCACHEPREFIX=/dev/shm/univet-stock-pycache .venv/bin/python -m compileall -q .` e `git diff --check`: aprovados.
- Commit/push e homologação online (reload e testes específicos das rotas novas) são etapas pendentes; não reaplicar seed nem alterar os três produtos QA históricos.
