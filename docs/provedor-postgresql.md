# Provedor PostgreSQL para o piloto — decisão técnica

Atualizado em 22/09/2026. Nenhuma conta foi criada, nenhum cartão foi cadastrado e nenhum provedor foi alterado.

## Decisão

Para o piloto acadêmico, a recomendação é **Neon Free**, com dois projetos independentes:

- `univet-demo`: somente dados fictícios;
- `univet-clinica`: schema inicialmente vazio e, somente após aprovação, dados da clínica.

O código Flask usa `DATABASE_URL` PostgreSQL padrão; a migração usa conexão direta e a aplicação usa pool limitado. A recomendação é condicional: o operador deve confirmar, durante o cadastro, que a conta permanece no plano Free e não solicita cartão. Não fazer upgrade para Launch/Scale e não habilitar qualquer recurso faturável.

## Comparação atual

| Opção | Free atual | Limites relevantes | SSL/conexão | Backup/restore | Avaliação |
|---|---|---|---|---|---|
| **Neon Free** | US$ 0/mês; a documentação atual descreve 100 projetos | 0,5 GB/projeto, 100 CU-h/projeto/mês, 5 GB de transferência, 10 branches/projeto; escala a zero após 5 min | PostgreSQL por connection string; confirmar `sslmode=require`/`verify-full` conforme certificado | histórico de restauração de 6 h e 1 snapshot manual; não substitui `pg_dump` diário | **Recomendado** para piloto pequeno e intermitente, desde que o banco esteja em projeto separado e o backup externo seja nosso |
| **Supabase Free** | US$ 0; até 2 projetos ativos | 500 MB de banco/projeto, 5 GB egress, 1 GB Storage; pausa após 1 semana de inatividade | conexão direta IPv6; pooler compartilhado IPv4; SSL `require` ou `verify-full` com CA | backups automáticos não estão incluídos no Free; documentação recomenda `supabase db dump`/exportação externa | Boa alternativa; exige atenção a IPv4/pooler, pausa e ausência de backup gerenciado |
| **Render Postgres Free** | US$ 0, mas expira | 1 GB, um banco Free por workspace, expira em 30 dias + 14 dias de carência | integração simples no Render | sem backups no Free | **Rejeitado** para semestre/piloto por expiração e falta de backup |

## Por que Neon foi escolhido

Neon atende melhor ao cenário de duas bases pequenas, com connection string PostgreSQL, isolamento por projeto e escala a zero. Supabase permanece plano B se o cadastro do Neon exigir cartão, se a região/conectividade não funcionar no Render ou se o limite de 0,5 GB não for suficiente. Render não atende à continuidade por expiração de 30 dias.

Fontes oficiais consultadas em 22/09/2026:

- [Neon — planos e limites](https://neon.com/docs/introduction/plans)
- [Neon — conexão](https://neon.com/docs/connect/connect-from-any-app)
- [Supabase — preços e Free](https://supabase.com/pricing)
- [Supabase — conexões, pooler e SSL](https://supabase.com/docs/guides/database/connecting-to-postgres)
- [Supabase — backups](https://supabase.com/docs/guides/platform/backups)
- [Render — Free](https://render.com/docs/free)

## Ação humana necessária

1. Criar/confirmar conta gratuita no Neon sem cartão.
2. Criar dois projetos separados, escolher região próxima do Render e copiar as duas URLs privadas.
3. Não enviar URLs, senhas ou certificados pelo chat; configurar `DEMO_DATABASE_URL` e `DATABASE_URL` como secrets distintos.
4. Confirmar ao responsável do projeto se o plano permanece Free e se a política de retenção atende ao piloto.

Enquanto essa ação não ocorrer, não existe `DEMO_URL`/`CLINICA_URL` nova homologada e o status permanece **NÃO APTO PARA DADOS REAIS**.

## Regras de custo

- Não cadastrar cartão.
- Não mudar de Free para plano pago.
- Monitorar armazenamento, CU-hours e transferência.
- Fazer `pg_dump` diário para armazenamento local seguro fora do Git; o provedor não é o único backup.
- Se o Free pedir cartão, cobrar excedente ou mudar a política, interromper e usar Supabase Free como alternativa, sujeito à mesma confirmação humana.
