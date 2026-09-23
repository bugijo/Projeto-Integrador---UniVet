# Matriz de testes e homologação

Atualizada em 23/09/2026. `OK local` não significa aprovação de produção.

| Funcionalidade | SQLite | PostgreSQL | DEMO | PRODUÇÃO | Resultado |
|---|---:|---:|---:|---:|---|
| Inicialização sem seed em produção | OK local | OK local | Schema remoto migrado, seed fictício | Schema remoto migrado, sem dados de negócio | Parcial remoto |
| Login, sessão e primeiro acesso | OK local | OK local | Pendente URL | Pendente conta | Regressão local |
| Tutores, pets e histórico clínico | OK local | OK HTTP | Pendente URL | Pendente fluxo | Sem dados reais |
| Consultas e agenda concorrente | OK local | Parcial/HTTP local | Pendente | Pendente | Repetir na arquitetura final |
| Produtos, lotes e FEFO | OK local | OK | Pendente | Pendente | Integridade local comprovada |
| Uso em consulta e baixa | OK local | OK | Pendente | Pendente | Integridade local comprovada |
| Estorno, ajuste e saldo não negativo | OK local | OK | Pendente | Pendente | Concorrência local comprovada |
| Migrações Alembic | SQLite legado | OK local | OK remoto | OK remoto | SSL `verify-full`, sem seed clínico |
| Backup/restore | OK local | OK local | Dump/restore remoto em projeto separado | Procedimento ainda não ligado ao serviço | 22 tabelas e fingerprints equivalentes |
| Restart/redeploy preservando dados | Não aplicável ao alvo | Não homologado remoto | Pendente | Pendente | Bloqueador |
| HTTPS, cookies e headers | Teste local | Não remoto | Pendente | Pendente | URL atual não é clínica |
| Carga 1/5/10/20/30/50 | Snapshot SQLite | Parcial local: 1/5 OK; maiores limitados por mesma conta | Pendente | Não executar sem limites | Repetir com contas independentes |
| Soak 10 usuários | 1 timeout anterior | 120 s limitado por mesma conta | Pendente | Não executar ainda | Repetir por 10–20 min com identidades independentes |
| Conta `DrFernanda` | Não criada | Não criada | Não | Não | Condicionada a zero bloqueadores |

## Evidência atual

- SQLite: 114 testes OK e 37 skips no modo sem PostgreSQL.
- PostgreSQL local: 14 testes HTTP e 24 testes de estoque/concorrência OK; o teste adicional cobre o formato de timestamp na agenda.
- PostgreSQL backup/restore local: 22 tabelas comparadas por fingerprint.
- Os 37 skips são grupos opt-in de PostgreSQL no modo SQLite; devem ser executados no job PostgreSQL do CI antes da liberação.
- O run de CI `35715470083` executou os grupos PostgreSQL em job separado e terminou com sucesso; os skips permanecem somente na execução SQLite por desenho.
- A carga pós-correção confirmou 0 falhas nos perfis de 1 e 5 usuários. Os perfis maiores e o soak não são conclusivos porque reutilizaram `admin` e acionaram o limite de login; repetir com contas fictícias independentes.

## Critério de passagem

Produção só pode passar quando a coluna `PRODUÇÃO` tiver evidência real para persistência, HTTPS, isolamento, backup/restore e restart/redeploy. Nenhum `skip` de segurança pode ser usado como aprovação.
