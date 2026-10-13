# Auditoria de custos do workspace Render

Atualizado em 23/09/2026. Consulta somente leitura pelo Render MCP. Nenhum billing, cartão, serviço ou variável foi alterado.

## Workspace

| Campo | Resultado |
|---|---|
| Workspace | My Workspace |
| ID | `tea-d1jh3rnfte5s73dj2ah0` |
| Recursos listáveis pelo MCP | 6 serviços; 0 PostgreSQL; 0 Key Value |
| Billing/fatura/cartão | Não expostos pelas ferramentas MCP disponíveis |
| Spend limit | Não exposto pelas ferramentas MCP disponíveis |

## Inventário de serviços

| Recurso | Tipo | Plano | Status | Repositório/branch | URL | Uso observado |
|---|---|---|---|---|---|---|
| `rpg-alpha` | Web Service Node | **Starter — PAGO** | ativo | `bugijo/Mestre-3D-T` / `alpha-online` | `https://rpg-alpha.onrender.com` | 1 instância contínua; 2 respostas HTTP e ~0,001 MB nas últimas 24 h |
| `eumaeus-frontend-staging` | Static Site | Starter | não identificado no MCP | `bugijo/eumaeus-system` / `codex/eumaeus-p1-staging-fixes` | `https://eumaeus-frontend-staging.onrender.com` | sem métricas no período consultado |
| `eumaeus-backend-staging` | Web Service Node | Free | não identificado no MCP | `bugijo/eumaeus-system` / `codex/eumaeus-p1-staging-fixes` | `https://eumaeus-backend-staging.onrender.com` | sem métricas no período consultado |
| `comanda-3setores` | Web Service Node | Free | não identificado no MCP | `bugijo/Lanchonete-` / `claude/analyze-system-improvements-PUnCD` | `https://comanda-3setores.onrender.com` | sem métricas no período consultado |
| `univet` | Web Service Python | Free | não suspenso | `bugijo/Projeto-Integrador---UniVet` / `main` | `https://univet.onrender.com` | sem métricas no período consultado |
| `Eumaeus-backend-oregon` | Web Service Node | Free | não identificado no MCP | `bugijo/eumaeus-system` / `main` | `https://Eumaeus-backend-oregon.onrender.com` | ~0,00025 MB nas últimas 24 h |

O roteiro chamou o recurso de `rp-alpha`; o inventário oficial retornou `rpg-alpha`. A identificação deve ser confirmada antes de qualquer mudança.

## Recursos não encontrados ou não expostos

- PostgreSQL Render: nenhum encontrado. Os bancos UniVet continuam no Neon Free.
- Key Value/Redis: nenhum encontrado.
- Cron Jobs, Background Workers, Private Services, persistent disks, private links, environment groups e add-ons: não há ferramentas MCP de listagem disponíveis nesta sessão; não é possível declarar inexistência somente com essa API.
- Billing, faturas, cartão e spend limits: não são expostos pelas ferramentas MCP disponíveis.

## Ações realizadas

Nenhuma alteração. Não foi feito downgrade, suspensão, exclusão, alteração de cartão ou billing. O serviço `univet` foi preservado.

## Ação humana necessária

1. Confirmar que `rpg-alpha` é o serviço referido como `rp-alpha`.
2. No Render Dashboard, abrir `rpg-alpha` → Settings → Instance Type/Plan.
3. Selecionar `Free`, confirmar o aviso de downgrade e verificar se não há persistent disk ou outro recurso dependente.
4. Abrir Billing e confirmar a fatura histórica e o acumulado do mês; downgrade não apaga valores já faturados.
5. Confirmar que não existe outro serviço pago, disco pago, worker, cron ou add-on no painel.
6. Verificar que o método de pagamento não será usado para novos excedentes; não remover o cartão automaticamente.

Depois do downgrade, revisar Usage/Billing e confirmar que o custo futuro previsto é US$ 0,00. Render informa que instâncias Free podem ser suspensas ao exceder limites; com método de pagamento, excedentes de bandwidth/build podem ser cobrados. [Render Free](https://render.com/docs/free) e [FAQ de billing](https://render.com/docs/faq).

## Estado de custo

O custo recorrente ainda **não pode ser declarado como US$ 0,00**, porque `rpg-alpha` permanece em `starter` e o MCP não permite downgrade. A fatura histórica e o acumulado atual também não puderam ser confirmados por MCP.
