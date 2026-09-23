# Hospedagem da Clínica — avaliação sem custo

Atualizado em 23/09/2026. Nenhum serviço novo foi criado nesta avaliação. A decisão considera apenas um pequeno piloto acadêmico, com PostgreSQL persistente no Neon e sem dados reais.

| Provedor | Plano | Cartão? | Cobrança automática? | Sleep? | HTTPS | Python/Flask | Secrets | Limites | Risco | Conclusão |
|---|---|---|---|---|---|---|---|---|---|---|
| Render | Free Web Service | Não é necessário para permanecer Free; confirmar no workspace | Sem cartão, a plataforma suspende quando haveria cobrança; com cartão pode cobrar excedentes | 15 min sem tráfego; retorno pode levar cerca de 1 min | TLS gerenciado | Sim | Variáveis de ambiente | 750 h/mês, bandwidth/build egress, um único worker, filesystem efêmero | suspensão por tráfego/uso; headers e secrets precisam ser verificados no serviço novo | **Melhor encaixe técnico, condicionado à confirmação humana de billing e plano Free** |
| Vercel | Hobby/Free | Não confirmado nesta avaliação | Limites e regras dependem da conta; não assumir ausência de cobrança sem confirmação | Modelo serverless, não processo Gunicorn contínuo | Sim | Python/Flask em Functions | Sim | runtime Beta, limites de duração/bundle; exige adaptação para `api/`/handler | aplicação Flask atual não é deploy direto como web service; mudanças de arquitetura e sessão precisam ser validadas | Plano B técnico, não escolher agora |
| Railway | Trial/Free | Trial pode iniciar sem cartão | Trial é crédito temporário; Free tem US$ 1/mês e uso limitado; não usar sem confirmar billing | Não é o foco principal | Sim | Sim via deploy Git/Docker | Sim | trial de 30 dias/US$ 5; rede pode ser restrita sem verificação GitHub | pode exigir upgrade após trial e não atende à garantia de semestre sem custo | Rejeitado para este piloto |
| Fly.io | Trial | Organização exige cartão | Uso é faturado; não há free tier permanente | Não aplicável como garantia | Sim | Sim via container | Sim | trial de 2 h ou 7 dias | cartão obrigatório e cobrança por recurso | Rejeitado |
| Koyeb | Free Instance | Cartão obrigatório para validar a organização | Starter é pay-per-use; excedentes são cobrados | Escala a zero após 1 h | Sim | Compatível por container/Git | Sim | 1 instância Free, 512 MB, 0,1 vCPU, 2 GB; uma região | pré-autorização de US$ 29 e cobrança de uso fora do Free | Rejeitado |

## Decisão

O Render Free é o candidato mais simples porque já hospeda o Demo, aceita Flask/Gunicorn, GitHub, HTTPS e variáveis de ambiente. O banco Neon separado elimina a dependência de filesystem persistente. Ainda assim, a criação do serviço Clínica exige **AÇÃO HUMANA NECESSÁRIA** para confirmar no painel que:

1. o serviço será criado com plano `Free`;
2. não há cartão ou método de pagamento ativo no workspace;
3. não será habilitado plano pago, persistent disk, worker, cron ou add-on;
4. o uso previsto é pequeno e aceita sleep/suspensão por limite;
5. as variáveis `DATABASE_URL`, `SECRET_KEY` e `UNIVET_ENV` serão inseridas como secrets sem exibição.

Sem essa confirmação, nenhum serviço novo deve ser criado automaticamente.

## Fontes oficiais

- [Render — Deploy for Free](https://render.com/docs/free)
- [Render — primeiro deploy](https://render.com/docs/your-first-deploy)
- [Render — FAQ de cobrança](https://render.com/docs/faq)
- [Vercel — runtime Python/Flask](https://vercel.com/docs/functions/runtimes/python)
- [Vercel — variáveis de ambiente](https://vercel.com/docs/environment-variables)
- [Railway — Free Trial](https://docs.railway.com/pricing/free-trial)
- [Fly.io — custo e free tier](https://fly.io/docs/about/cost-management/)
- [Koyeb — instâncias Free](https://www.koyeb.com/docs/reference/instances)
- [Koyeb — cobrança e cartão](https://www.koyeb.com/docs/faqs/pricing)
