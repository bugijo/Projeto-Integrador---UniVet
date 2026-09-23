# Runbook — preparação local, não liberação da clínica

Atualizado em 23/09/2026. **NÃO APTO PARA DADOS REAIS.** Ver `prontidao-clinica.md`, `provedor-postgresql.md`, `hospedagem-clinica.md` e critérios de liberação. Neon Free foi provisionado em dois projetos, com migrations remotas e restore ensaiado em banco separado; nenhum serviço web clínico foi publicado. Não executar estes exemplos sobre banco real sem confirmação, backup e janela operacional.

## Ambientes

Mesmo código; processos, URLs, bancos, chaves e backups distintos. Não existe botão para trocar ambiente.

- Desenvolvimento: `UNIVET_ENV=development`, `UNIVET_DATABASE` local; demo somente com seed explícito.
- Demo: `UNIVET_ENV=demo`, `DEMO_DATABASE_URL=sqlite:////caminho/absoluto/demo.db`; segredo próprio estável para múltiplos workers. Somente dados fictícios.
- Produção local candidata: `UNIVET_ENV=production`, `DATABASE_URL=sqlite:////caminho/absoluto/clinica.db`, `UNIVET_SQLITE_PERSISTENT=1`, `SECRET_KEY` privada com pelo menos 32 caracteres, HTTPS. A flag é declaração do operador, não prova de persistência.
- **Render + SQLite de produção é recusado**, mesmo com a flag. PostgreSQL é obrigatório em produção publicada; URL inválida falha explicitamente, nunca cai silenciosamente em SQLite. Neon remoto foi migrado; serviço clínico e recovery permanecem pendentes.
- Não definir `UNIVET_DATABASE` nos ambientes publicados. Não compartilhar caminhos (inclusive aliases), chaves, dumps ou diretórios. Marcação interna do banco recusa outro ambiente e recusa adotar banco legado sem revisão.
- `UNIVET_TRUST_PROXY=1` somente atrás de um proxy confiável, sem acesso direto ao backend. Cookies de produção Secure/HttpOnly/Lax, DEBUG desligado.

Para a arquitetura pretendida, manter dois serviços Render: o serviço Demo existente, sem alterações destrutivas, e um novo serviço Clínica isolado apontando para o branch aprovado. Cada serviço recebe variáveis e secrets próprios; `DEMO_DATABASE_URL` nunca deve aparecer no serviço Clínica.

## Inicialização limpa e migração

Em banco NOVO configurado, `.venv/bin/python init_db.py` cria estrutura sem usuários, pacientes, consultas, produtos ou fornecedores fictícios. Espécies/raças/serviços são configurações estruturais. Em demo NOVA, seed explícito: `.venv/bin/python init_db.py --demo`.

Banco legado já populado e sem marca de ambiente é recusado em demo/produção: não inserir marca manualmente nem sobrescrever o original. Planejar migração revisada de cópia fictícia. O inicializador ainda contém migrações legadas e não substitui um pipeline PostgreSQL versionado. Não o executar no serviço dos professores durante esta preparação.

## Contas e primeiro acesso

CLI exige banco existente compatível com o ambiente. Operador local confiável, terminal interativo SEM gravação, sem pipe/tee, sem CI. A senha temporária aleatória é mostrada uma vez após sucesso. Entrega privada, não no chat/Git/log/documentação. O programa não consegue detectar gravação externa do terminal.

Exemplos futuros, somente após homologação:

```bash
.venv/bin/python admin_cli.py --database /caminho/aprovado/clinica.db bootstrap --login gestor --name 'Administrador'
.venv/bin/python admin_cli.py --database /caminho/aprovado/clinica.db create-user --login DrFernanda --name 'Dra. Fernanda' --role veterinaria
.venv/bin/python admin_cli.py --database /caminho/aprovado/clinica.db reset-password --login DrFernanda
.venv/bin/python admin_cli.py --database /caminho/aprovado/clinica.db deactivate --login DrFernanda
```

**DrFernanda não foi criada; nenhuma senha dela foi gerada.** Bootstrap também exige primeiro acesso. Criação recusa duplicidade; reset revoga sessões e gera nova senha temporária; desativação preserva autoria e recusa remover último administrador.

Primeiro login mostra apenas “Defina sua nova senha” e saída. Demais telas ficam bloqueadas; APIs respondem 403. Troca exige senha atual, confirmação, 12–128 caracteres e diferença da anterior. Após sucesso, senha temporária inválida, sessões anteriores revogadas, nova sessão e dashboard. Troca voluntária posterior exige novo login. Senha definitiva só é digitada pela titular.

## Backup e restauração

Implementado para SQLite, inclusive origem em WAL; comandos não importam app nem executam seed:

```bash
.venv/bin/python maintenance.py backup /caminho/aprovado/clinica.db /backup/privado/clinica-data.db
.venv/bin/python maintenance.py restore /backup/privado/clinica-data.db /ensaio/novo/restaurado.db
```

Destino precisa ser NOVO. Fonte read-only, snapshot consistente, arquivo 0600, integridade/FKs e SHA-256; não sobrescreve banco, nem troca serviço automaticamente. Backups mantêm identidade do ambiente: dump demo não vira produção. Proteger também diretórios, mídia e transporte; 0600 não é criptografia.

Proposta pendente de responsável nomeado: backup diário e antes de deploy/migração; 7 diários e 4 semanais em meio privado fora do host; restore mensal e antes da liberação; RPO proposto 24 h, RTO a medir no alvo. Não foi configurado agendamento nem destino externo. Sem restore do alvo, recuperação de produção = NÃO VALIDADA.

Ensaios automatizados locais: dados fictícios, backup, remoção apenas da origem temporária criada no teste, restore e comparação integral de schema/registros, FKs, saldo e usuários. Não equivale a backup da clínica ou restore PostgreSQL.

## Deploy e rollback

Nenhum deploy autorizado nesta rodada. Identificar backend/URLs e configurar serviços separados antes de publicar. URL anteriormente conhecida `https://univet-frontend.onrender.com/login` retornou 404 na consulta de 19/09; não confirma backend nem disponibilidade atual.

Não aplicar `render.yaml` atual: modo produção sem banco persistente deve falhar. Preservar demo online até migração explicitamente aprovada. CI atual é teste + GET, não atestação de publicação.

Antes do corte: suíte completa, backup restaurável, fingerprint do commit e revisão dos commits ancestrais. Depois: confirmar mesmo SHA em health/painel, HTTPS, dado fictício sobrevivendo restart E redeploy, fluxos autenticados e restore. `/health` acessa banco pelo middleware, mas SHA informado pelo ambiente não prova sozinho implantação.

Rollback exige código/schema compatíveis e preservação de novas escritas; trocar para backup antigo pode perder dados. Não force-push. PDFs continuam no histórico remoto (SEC-12); qualquer saneamento requer autorização específica.

## Monitoramento gratuito e incidente

Usar ferramentas locais do SO e logs redigidos do servidor: checagem HTTPS de `/health` a cada 5 minutos por agendador existente, alerta ao responsável após falha; verificar exit code de backup e idade da última cópia diariamente. Implementação/agendamento e canal de alerta no alvo ainda pendentes. Não enviar prontuários/CPF/tokens ao monitoramento.

Erro 500, banco indisponível, backup ausente ou segredo exposto: aplicar `plano-incidente.md`, manter processo anterior da clínica como contingência e registrar somente horário/serviço/status/commit. Responsáveis e contatos devem ser aprovados privadamente.
