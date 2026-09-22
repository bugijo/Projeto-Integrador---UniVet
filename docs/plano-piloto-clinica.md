# Plano de piloto controlado — UniVet Clínica

Documento preparatório. O piloto ainda não está liberado.

## Condições de entrada

- PostgreSQL persistente gratuito homologado e separado do Demo;
- schema aplicado por migration, sem seed fictício;
- backup diário externo e restore ensaiado em banco separado;
- HTTPS, secrets exclusivos, DEBUG desligado e cookies seguros;
- conta individual criada somente após aprovação técnica;
- contingência manual da clínica definida.

## Primeira semana

- começar com poucos usuários autorizados;
- manter o processo anterior como contingência;
- realizar backup diário e registrar hash/horário sem dados pessoais;
- acompanhar erros 500, falhas de conexão, latência e execução dos backups;
- registrar bugs, dúvidas e incidentes em documento privado do projeto;
- não executar carga artificial nem cadastrar dados desnecessários.

## Revisão após a primeira semana

- conferir se os backups foram produzidos e se um restore de teste foi possível;
- revisar consumo de armazenamento, CU-hours/limites e reinícios;
- revisar acessos, sessões, exportações e logs;
- coletar feedback dos usuários;
- decidir se o piloto continua, volta à contingência ou é encerrado.

## Monitoramento gratuito e simples

- health check HTTP de baixa frequência;
- logs do Render sem dados pessoais;
- planilha local de backup, incidentes e indisponibilidade;
- alerta manual por e-mail institucional quando houver falha;
- sem adicionar ferramenta paga ou serviço que exija cartão.

## Saída do piloto

O resultado deve registrar: incidentes, tempo de indisponibilidade, backups realizados, restores testados, erros, latência observada e decisão da clínica. **Apto para piloto controlado** não significa aprovação para uso operacional definitivo.
