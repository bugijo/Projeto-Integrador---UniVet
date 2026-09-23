# Prontidão da clínica — 23/09/2026

## Parecer

**NÃO APTO PARA DADOS REAIS.** Os bancos Neon Free foram criados e o schema remoto foi migrado, mas operação dos dois serviços, recuperação no alvo e validação final permanecem pendentes. Não confundir banco provisionado ou teste verde com liberação clínica.

## Arquitetura atual e pretendida

Mesmo código Flask/Jinja/JS; processos e configurações diferentes; sem chaveamento pela interface. `config.py` seleciona banco explicitamente; banco identificado por ambiente, cookies e assinatura separados, segredo próprio recomendado. Startup publicado não inicializa schema/seed automaticamente.

| Item | DEMO | PRODUÇÃO |
|---|---|---|
| URL | `https://univet.onrender.com` (serviço atual na `main`; não é homologação clínica) | Não provisionada/confirmada |
| Configuração | `UNIVET_ENV=demo`, `DEMO_DATABASE_URL` | `UNIVET_ENV=production`, `DATABASE_URL` |
| Banco | Neon `univet-demo`, seed exclusivamente fictício | Neon `univet-clinica`, schema migrado e dados de negócio zerados; restore ensaiado em banco separado |
| Usuário | `admin`, conta de avaliação existente no seed demo; não se tentou login online | Primeiro administrador e `DrFernanda` NÃO criados |
| Dados | Exclusivamente fictícios; demo online não modificada | Base real não criada/manipulada; ensaios de produção usam base descartável vazia/fictícia |
| Situação | Navegação/estoque/consultas demonstrativos passam localmente | Bloqueada para uso real |

Não aplicar manifesto atual em main/Render: configuração segura incompleta deve falhar, não substituir demo silenciosamente. Bancos antigos sem marca de ambiente exigem revisão/migração, não são adotados automaticamente. URLs SQLite não significam suporte PostgreSQL por simples troca de prefixo.

## Segurança e testes

Controles locais: CSRF, hash Werkzeug, sessão revogável/expiração/rotação, primeiro acesso obrigatório, reset administrativo com senha aleatória em TTY, RBAC no servidor, CSV anti-fórmula, proteção API, limites de tentativas e de entradas, headers/CSP/HSTS, separação de ambientes e rejeição de seed/credencial demo em produção.

Clínica: histórico de cadastros e alterações na mesma transação; consulta cancelada em vez de apagada; concluídas, condições e autoria protegidas de exclusão. Agendamentos sem atendimento podem ser redistribuídos com registro de histórico ao remover profissional; política completa de adendos ainda pendente.

Checkpoint final da rodada: **77 testes = 27 anteriores +50 novos; 77 passaram, 0 falharam**, em 18,673 s, log `artifacts/final-ci-command-tests.log`. Comando de descoberta independente de PYTHONPATH como no CI. Inclui banco limpo, duas inicializações, primeiro acesso HTTPS e novo processo preservando conta fictícia. Não equivale a redeploy em nuvem nem fluxo clínico integral na futura arquitetura PostgreSQL.

## Banco, backup, restore e concorrência

- Backup/restore SQLite implementados por snapshot consistente, origem read-only, destino novo 0600 e hash/integridade/FKs. O procedimento remoto também foi ensaiado em projeto Neon separado com 22 tabelas, 28 FKs e fingerprints equivalentes; ainda falta agendamento, retenção e restore operacional do serviço clínico.
- Concorrência SQLite: 2/5/10 conexões, FEFO, saídas/uso clínico, ajustes/estornos, saldo insuficiente, rollback e agenda. Estorno único por restrição no banco. Nenhum dado real utilizado.
- PostgreSQL: aplicação/migração/dump/restore remoto e local aprovados em ambientes separados; serviço web, restart/redeploy e recuperação operacional do alvo ainda pendentes. Ver `plano-migracao-banco.md`.
- Migrações SQLite ainda incluem rotinas legadas; revisar todas as constraints incrementais e evolução antes da clínica. Marca de versão de segurança não substitui pipeline completo.

## Carga e ferramentas

Seis perfis curtos 1/5/10/20/30/50 sem erros após WAL. Soak 10 usuários/10 minutos: **um timeout em 37.680 requisições**. Integridade permaneceu íntegra, mas estabilidade não aprovada plenamente. Snapshot anterior às alterações desta rodada; repetir na versão final. Detalhes em `relatorio-carga.md`.

Codex Security 0.1.29 funciona com Node22 temporário; dry-run antes/depois, autenticação não verificada, **sem scan efetivo/pago**. pip-audit repetido em 21/09: 12 pacotes/zero advisories. Bandit final: dois médios revisados (bind e SQL interno de paginação). Não afirmar ausência de vulnerabilidades.

## Privacidade e operação

Documentos: `privacidade-dados.md`, `runbook-producao.md`, `plano-incidente.md`, `plano-piloto-clinica.md`, `entrega-dra-fernanda.md`. Responsáveis, retenção/RPO/RTO, meio externo de backup e alertas ainda devem ser definidos/ensaiados. Não houve serviço pago, cartão, integração externa nova, push ou deploy.

## Pendências de liberação

Classificação detalhada em `auditoria-seguranca.md`: **2 bloqueadores, 2 altos, 3 médios, 0 baixos** ainda abertos nesta avaliação.

1. Implementar e testar adaptação PostgreSQL completa, migrações/restore e tipos/constraints; ou homologar explicitamente alternativa persistente local sem alegar nuvem pronta.
2. Escolher infraestrutura gratuita adequada e confirmar URLs/backend, configuração e SHA; autorização antes de alterar serviços/dados reais.
3. Provar persistência depois de restart/redeploy e recuperação do alvo com backups externos.
4. Concluir integridade clínica/adendos, precisão financeira, semântica de estornos, caches multiprocesso e fluxo completo.
5. Investigar timeout, repetir carga/soak e suíte/QA na versão final.
6. Aprovar responsáveis, política de dados, incidente e piloto acompanhado.
7. Decidir saneamento dos PDFs no histórico remoto com autorização específica. Não houve reescrita.

Conta DrFernanda: comando preparado; conta não criada; senha não gerada nem commitada. Somente após aprovação dos critérios emitir temporária privadamente. Primeira classificação possível será **APTO PARA PILOTO CONTROLADO**, não segurança absoluta.
