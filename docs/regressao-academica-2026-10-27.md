# Regressão acadêmica UniVet — 26–27/10/2026

URL: https://bugijo.pythonanywhere.com — PythonAnywhere Free, custo desta rodada $0, sem cartão/upgrade. Base Git: `3b0af2e` em `main`. Exclusivamente dados fictícios.

## Evidências locais

Suíte: `TMPDIR=/dev/shm .venv/bin/python -m unittest discover -s tests -v`.

- 135 testes; 97 passaram; zero falhas/erros; 38 skips PostgreSQL opt-in; 35,707 s.
- PostgreSQL separado: `TMPDIR=/dev/shm UNIVET_TEST_POSTGRES=1 PYTHONPATH=tests .venv/bin/python -m unittest test_postgres -v`: 38 passaram; zero falhas; 65,585 s. Os skips da suíte principal foram, portanto, executados nesta etapa separada.
- 15 regressões novas em `tests/test_academic_regressions.py`. Incluem fluxo HTTP de cadastros, três lotes, FEFO, estorno, ajuste, consulta/animal, CSV UTF-8/injection, API, logout, replay, duas conexões simultâneas, assets versionados e ordenação de timestamps legados.
- `compileall`, `node --check static/js/navigation.js` e `git diff --check`: aprovados.
- Os primeiros ensaios sofreram timeouts de subprocessos e de inicialização Docker, com disco local em 99% e espera de I/O. Reexecução SQLite em tmpfs e PostgreSQL com PGDATA temporário em tmpfs passou. Nenhum controle de segurança ou asserção foi desabilitado.
- Dois testes FEFO antigos tinham data futura fixa já vencida em 20/10/2026; foram corrigidas as fixtures, preservando o teste de lote realmente vencido.

## Relatos e causas

| Item | Reproduzido antes? | Causa/evidência | Correção | Automação | Online |
| --- | --- | --- | --- | --- | --- |
| Movimentações | Sim, local e log remoto | `sqlite3.Row` sem `valor_total`; Jinja falhava ao formatar o total | SIM: SELECT retorna quantidade × valor praticado, preservando NULL; datas com espaço/T ordenadas corretamente | Sim | SIM, HTTP 200 com filtros/refresh/paginação |
| Registrar saída | Sim: erro no redirect e falta de proteção a replay | Commit ocorria antes de renderizar a página seguinte; repetir POST podia baixar novamente | SIM: total corrigido, confirmação explícita, chave assinada por formulário e registro atômico sob lock | Sim, inclusive concorrência | SIM, reenvio não deduziu novamente |
| Botão em Produtos | Sim | Ausente na lista/detalhe; parâmetro GET ignorado | SIM: botão e rota única com produto selecionado | Sim, preseleção HTTP | SIM, botão do produto QA abriu produto 11 selecionado |
| Produto na consulta | Fluxo existente; risco de reenvio confirmado | Baixa já era transacional e vinculada à consulta; faltava deduplicação HTTP | SIM: chave por formulário/consulta, preservando vínculo ao animal via consulta | Sim, múltiplos produtos/rollback/replay | SIM, dois produtos na consulta QA 8 e paciente QA 11 |
| Moeda | Sim | `%.2f` com ponto decimal e espaço quebrável | SIM: `moeda_br`, NBSP e `Intl.NumberFormat` nos cálculos de formulário | Sim, seis valores literais | SIM, exibição R$ com milhar e vírgula, em uma linha |
| Menu mobile | Sim, online | `position: static`; após scroll o menu estava acima da viewport, top ≈ -2899 px; cache antigo persistia mesmo após reload | SIM: drawer fixed abaixo da altura real do cabeçalho, scroll interno, Escape/fechamento e hash de conteúdo nas URLs CSS/JS | Sim: URL versionada automatizada e medições no navegador | SIM, 320–740 px e topo/meio/fim |
| Nomes com bolinhas | NÃO | Lista pública inspecionada: nomes em TD simples, pseudo-elementos before/after `none` | Não aplicada: problema não reproduzido. Nenhuma mudança de nomes/dados; regressão para Luna, Thor, Mel, Bob, São Bento, Joãozinho, Coração | Sim, UTF-8/renderização | SIM, nomes verificados sem marcadores, inclusive Coração QA |
| Relatórios mobile | Sim, local | Grid mantinha largura mínima do gráfico (~1950 px) e alargava a página | SIM: `min-width: 0` no card e coluna `minmax(0, 1fr)` | Medição no navegador | SIM, sem overflow da página |

### Saída: diagnóstico explícito

A saída era salva antes do redirect. A falha confirmada era na renderização de Movimentações. Havia risco de nova baixa se o usuário repetisse o envio. O novo identificador é independente do CSRF, assinado, vinculado ao usuário/escopo e verificado antes da escrita. O hash auditável fica em `security_events` na mesma transação da baixa; o lock existente serializa a verificação. Uma falha reverte tanto o registro da operação como os lotes/movimentações. Um novo formulário permite outra saída legítima.

### Dados e navegação

- Uso em consulta permanece Produto → Consulta → Animal → Tutor. Não foi criado vínculo direto Produto → Tutor.
- Saídas administrativas mantêm motivo livre e preço zero quando não há repasse. Lotes vencidos não entram no FEFO; ajuste auditado continua disponível para inventário/descarte do lote.
- Estorno e cancelamento preservam rastreabilidade. Nenhum histórico ou funcionalidade foi removido.
- Serviços continuam sendo procedimentos com duração para agenda; não se inventou tabela comercial clínica.

## Navegador local

- Menu após scroll: 320, 360×800, 375, 390×844, 412×915, 430 e 740 px; visível dentro da viewport, sem overflow horizontal da página.
- Desktop: 1366×768 e 1920×1080 — dashboard, estoque, produtos, movimentações e animais sem overflow da página.
- Mobile 360 px: tutores, animais, veterinários, serviços, consultas, histórico, estoque, produtos, lotes, entrada, saída, categorias, fornecedores, movimentações e relatórios. O overflow de relatórios foi reproduzido e eliminado; tabelas/gráfico mantêm scroll interno.

## Publicação

- Backup SQLite antes das alterações: `/home/Bugijo/univet-backups/pre-correcao-20261026.sqlite`, integridade e referências aprovadas. Arquivo privado fora do repositório.
- Não reaplicar `init_db.py --demo` ao banco existente.
- WSGI usa cookie `Secure`; Force HTTPS deve estar ativo no painel. HttpOnly, SameSite, CSRF, sessão revogável e autorização permanecem.
- Commit funcional implantado: `f40b52d` em `main`; os commits documentais posteriores não alteram o código homologado. Atualização por fast-forward, sem reset, rebase ou reaplicação do seed.
- Backup adicional imediatamente antes do reload: `/home/Bugijo/univet-backups/pre-reload-20261027.sqlite`, `integrity_check=ok`, `foreign_key_check=ok`; privado e fora do Git.

## Homologação pública concluída

- `/health`, `/login` e `/`: HTTP 200. HTTP redireciona para HTTPS, certificado validado pelo cliente, cookie de sessão Secure/HttpOnly/SameSite=Lax.
- Login válido e inválido; 16 páginas autenticadas em HTTP 200; cadastros fictícios de tutor, animal, veterinário, serviço, categoria e fornecedor aprovados.
- Produto QA A com lotes de 3, 5 e 7 unidades: saída de 4 consumiu 3 do primeiro lote e 1 do segundo. Reenvio da mesma operação manteve saldo 11. Nova saída legítima de 1,5 levou a 9,5. Pedido acima do saldo não alterou estoque.
- Uso de 2 unidades na consulta deixou 7,5; reenvio manteve 7,5. Segundo produto QA B, com entrada de 3 e uso de 1, permaneceu em 2. Ambos aparecem na consulta QA 8, vinculada ao animal QA 11.
- Movimentações: abrir, atualizar, filtrar, paginar, voltar e avançar no navegador sem tela de erro e sem nova baixa.
- Relatórios com e sem dados, APIs e três exportações CSV aprovados. CSV UTF-8 e proteção contra fórmula também cobertos pela suíte local.
- CSRF inválido: 400; API sem sessão: 401; veterinário impedido de cadastrar serviço/exportar CSV: 403. Logout por HTTP e pelo botão do navegador revogou o acesso.
- Mobile online: 16 telas em 390×844 sem overflow da página; menu após scroll em 320, 360×800, 375, 390×844, 412×915, 430 e 740 px. Topo/meio/fim e Escape aprovados em 360, 390, 412 e 740×360. Desktop 1366×768 e 1920×1080: dashboard, estoque, produtos, movimentações e animais sem overflow.
- Valor monetário público observado: `R$ 5.503,70`, NBSP entre símbolo/número e altura de uma linha. `5354 → R$ 5.354,00` verificado na regressão literal; nenhum saldo foi adulterado para produzir esse exemplo visual.
- Persistência após reload: saldos 7,5 e 2,0, dois itens na consulta e vínculo ao animal mantidos; sessão continuou válida. SQLite íntegro, zero violações de FK.
- Log histórico preservado. Baseline: 378 linhas; zero novos tracebacks no trecho a partir da linha 379 após deploy e homologação.
- Registros novos são identificados por prefixo `QA acadêmico 20261027-...`; mantidos com sua rastreabilidade. Nenhuma conta real, dado real ou `DrFernanda` foi criado.

Bloqueadores reproduzíveis nesta rodada: **nenhum**. O relato de bolinhas continua classificado como **não reproduzido**, não como causa identificada/corrigida.
