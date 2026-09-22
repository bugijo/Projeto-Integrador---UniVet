# Matriz de testes e homologação

Atualizada em 22/09/2026. `OK local` não significa aprovação de produção.

| Funcionalidade | SQLite | PostgreSQL | DEMO | PRODUÇÃO | Resultado |
|---|---:|---:|---:|---:|---|
| Inicialização sem seed em produção | OK local | OK local | Pendente remoto | Pendente remoto | Implementado localmente |
| Login, sessão e primeiro acesso | OK local | OK local | Pendente URL | Pendente conta | Regressão local |
| Tutores, pets e histórico clínico | OK local | OK HTTP | Pendente URL | Pendente fluxo | Sem dados reais |
| Consultas e agenda concorrente | OK local | Parcial/HTTP local | Pendente | Pendente | Repetir na arquitetura final |
| Produtos, lotes e FEFO | OK local | OK | Pendente | Pendente | Integridade local comprovada |
| Uso em consulta e baixa | OK local | OK | Pendente | Pendente | Integridade local comprovada |
| Estorno, ajuste e saldo não negativo | OK local | OK | Pendente | Pendente | Concorrência local comprovada |
| Migrações Alembic | SQLite legado | OK local | Pendente remoto | Pendente remoto | Sem rollback destrutivo |
| Backup/restore | OK local | OK local | Pendente | Pendente | Fingerprint local de 22 tabelas |
| Restart/redeploy preservando dados | Não aplicável ao alvo | Não homologado remoto | Pendente | Pendente | Bloqueador |
| HTTPS, cookies e headers | Teste local | Não remoto | Pendente | Pendente | URL atual não é clínica |
| Carga 1/5/10/20/30/50 | Snapshot SQLite | Pendente final | Pendente | Não executar sem limites | Repetir após PostgreSQL |
| Soak 10 usuários | 1 timeout anterior | Pendente final | Pendente | Não executar ainda | Investigar antes |
| Conta `DrFernanda` | Não criada | Não criada | Não | Não | Condicionada a zero bloqueadores |

## Evidência atual

- SQLite: 114 testes OK e 37 skips no modo sem PostgreSQL.
- PostgreSQL local: 13 testes HTTP e 24 testes de estoque/concorrência OK.
- PostgreSQL backup/restore local: 22 tabelas comparadas por fingerprint.
- Os 37 skips são grupos opt-in de PostgreSQL no modo SQLite; devem ser executados no job PostgreSQL do CI antes da liberação.

## Critério de passagem

Produção só pode passar quando a coluna `PRODUÇÃO` tiver evidência real para persistência, HTTPS, isolamento, backup/restore e restart/redeploy. Nenhum `skip` de segurança pode ser usado como aprovação.
