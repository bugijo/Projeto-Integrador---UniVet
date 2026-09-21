# Carga local — UniVet

## Estado

Atualizado em 21/09/2026: carga executada localmente em 19/09, com snapshots imutáveis e dados fictícios. Primeira execução com journal antigo apresentou 2 falhas em 478 requisições no perfil 20 e foi interrompida. Após WAL/busy timeout, os seis perfis passaram, mas **soak apresentou um timeout e NÃO está integralmente aprovado**. A versão medida precede isolamento/primeiro acesso e preservação clínica adicionados posteriormente; repetir na versão final. Nenhum teste contra Render.

Escopo exclusivo: `perf/` e este relatório. A skill local `.agents/skills/univet-testing/SKILL.md` orientou isolamento de ambos os módulos de banco, limites de recursos e separação entre carga e validação de segurança. A suíte geral e o teste da proteção de rate limit pertencem ao agente principal.

## Execução após autorização

Na raiz do repositório, com `uv`/`uvx` disponível:

```bash
python3 perf/run.py --help
# Somente após o agente principal confirmar auth pronta e janela estável:
python3 perf/run.py --authorized --soak
# Se o limitador impedir a medição, executar em janela separada:
python3 perf/run.py --authorized --soak --disable-rate-limit
```

`--authorized` registra a decisão operacional de executar; não detecta autorização automaticamente. Sem essa opção, o runner encerra antes de instalar dependências ou iniciar a aplicação. Mudanças durante a cópia interrompem a preparação; depois dela, o snapshot imutável mantém os processos em uma única versão, independente de alterações na árvore de trabalho.

Locust é gratuito/open source, executado via `uvx --isolated` em ambiente próprio, junto com Gunicorn e psutil; não instala nada no ambiente do projeto e não modifica `requirements.txt`. A primeira execução requer acesso ao índice de pacotes. As versões resolvidas são registradas em `metadata.json`; a faixa de Locust é `>=2.32,<3`. Referências: [ambientes de ferramentas uv](https://docs.astral.sh/uv/concepts/tools/) e [estatísticas/CLI Locust](https://docs.locust.io/en/stable/configuration.html).

## Isolamento e pré-requisitos

- O runner não aceita URL externa. Gunicorn usa `127.0.0.1`, porta efêmera, dois workers síncronos por padrão (`--workers 1` a `4`). Não há interface web Locust.
- Código, templates e estáticos são copiados para `tempfile.TemporaryDirectory`; nenhum banco, `.env`, `.venv` ou arquivo de produção é copiado. Cada perfil recebe banco novo dentro desse diretório, com `init_db(seed_demo=True)` apenas nesse banco.
- `UNIVET_ENV=development` e `UNIVET_DATABASE=<temporário>/<perfil>.db` são passados somente aos subprocessos. Antes do seed/servidor, `bench_app.py` exige que **ambos** `app.DATABASE` e `init_db.DATABASE` correspondam exatamente ao banco descartável. A aplicação precisa suportar essas opções; não há fallback para `banco.db`.
- Login padrão inicial: conta demo `admin` / `123456`. `UNIVET_BENCH_LOGIN` e `UNIVET_BENCH_PASSWORD` permitem usar outra credencial já presente no seed; não criam/resetam contas. Não usar credenciais reais. A futura CLI de senha não é necessária ao runner.
- Cada usuário mantém sessão própria, lê `csrf_token` dos formulários e envia o token no login e nas escritas. Token ausente, login recusado, redirecionamento inesperado e escrita sem confirmação são falhas. O runner não desativa CSRF.
- `--disable-rate-limit` define `UNIVET_RATE_LIMIT_ENABLED=0` exclusivamente nos filhos do benchmark. O fato consta em `metadata.json`. Esse resultado mede o app sem limitador e **não valida a proteção de rate limit**, cujo teste fica separado com o agente principal.
- Finalização encerra os grupos de processos iniciados e remove automaticamente a cópia/bancos temporários. Evidências persistem em `perf/results/<UTC>/` (ignorado pelo Git). Interrupção abrupta do sistema pode exigir limpeza manual do temporário identificado nos logs.

## Modelo de carga

Perfis sequenciais: **1, 5, 10, 20, 30 e 50 usuários**, **30 segundos por perfil**, com subida de até 5 usuários/s e até 10 segundos para finalizar tarefas pendentes. A janela inclui login e subida: com 50 usuários há cerca de 10 segundos de subida. Não é uma medição longa de estado estável. Cada perfil reinicia servidor e banco para comparar a mesma base demo.

Login é realizado uma vez por usuário. Após autenticar, cada usuário percorre os módulos e faz uma pequena escrita para garantir cobertura mesmo no perfil de um usuário. Depois, escolhe navegação/escrita com pesos 9:1, pausa de 0,5–1,5 s entre tarefas. Navegação agrupa oito GETs: dashboard (`/pagina-inicial`), tutores, pets, consultas/calendário, agenda do dia, estoque, produtos e relatórios. A escrita cria uma categoria fictícia de nome único e busca esse nome para confirmar persistência. Peso 9:1 é por tarefa, **não** 10% dos requests. Categorias crescem ao longo de cada perfil; contagens antes/depois são registradas. Não são criadas consultas ou movimentações financeiras/de estoque.

Soak opcional: **10 usuários, 600 segundos**, após os seis perfis sem falhas e com pelo menos 1 GiB disponível e CPU do host abaixo de 85% na checagem. Interrompe um perfil se RAM disponível cair abaixo de 256 MiB, CPU do host superar 98% durante 15 amostras consecutivas, servidor encerrar ou estourar o timeout externo. A sequência para no primeiro perfil com erro/interrupção/integridade inválida para permitir diagnóstico. Perfis não executados devem permanecer sem resultado; corrigir a causa e repetir a série em outra janela autorizada.

## Evidências e interpretação

`summary.md` e `summary.json` consolidam req/s, latência média/mediana/p95/p99 em ms, erros/total, CPU média da árvore Gunicorn e RSS pico. Arquivos `<perfil>_stats.csv`, `_stats_history.csv`, `_failures.csv`, `_exceptions.csv`, HTML e logs preservam dados por rota e falhas. `<perfil>-resources.csv` coleta aproximadamente a cada segundo CPU/RAM do servidor e do gerador separadamente, CPU total e memória disponível do host. JSON individual registra contagens antes/depois, `PRAGMA integrity_check` e quantidade de violações de chaves estrangeiras.

CPU do processo segue a convenção de 100% por núcleo e pode superar 100%; a primeira amostra não entra na média. RSS soma master/workers e pode contar páginas compartilhadas mais de uma vez; não representa PSS nem consumo exclusivo. Percentis do Locust são aproximados. Métricas agregadas incluem login, leitura e escrita; verificações sintéticas de CSRF aparecem como `CHECK` apenas quando há falha. Inspecionar também as linhas por rota e a quantidade de usuários alcançada no histórico.

Servidor e Locust compartilham o mesmo host; hardware, versões e hashes constam em `metadata.json`. A base é pequena/fictícia, os ativos estáticos/JS não são executados como num navegador, e autenticações simultâneas podem dominar os perfis curtos. Não extrapolar esses números para produção, volume real de dados, máximo de usuários suportados ou aprovação de segurança. Metas de latência/capacidade ainda precisam ser definidas para homologação.

## Resultados

| Usuários | Duração | Req/s | Média | Mediana | p95 | p99 | Erros | CPU/RAM |
|---:|---:|---|---|---|---|---|---|---|
| 1 | 30 s | 7,35 | 19,62 | 16 | 28 | 170 | 0/212 | 9,94% / 108,46 MiB |
| 5 | 30 s | 36,33 | 19,68 | 14 | 28 | 220 | 0/1.043 | 36,71% / 169,12 MiB |
| 10 | 30 s | 69,49 | 19,00 | 12 | 33 | 190 | 0/2.026 | 60,72% / 166,49 MiB |
| 20 | 30 s | 130,71 | 21,18 | 12 | 60 | 240 | 0/3.811 | 93,33% / 168,43 MiB |
| 30 | 30 s | 169,99 | 40,96 | 16 | 170 | 400 | 0/4.965 | 116,64% / 168,82 MiB |
| 50 | 30 s | 211,69 | 84,05 | 51 | 270 | 670 | 0/6.193 | 145,28% / 168,81 MiB |
| 10 (soak) | 10 min | 62,90 | 23,52 | 13 | 58 | 160 | **1/37.680** | 57,12% / 148,54 MiB |

Tempos em ms; CPU média/RSS pico do servidor. Fonte: `perf/results/20260919T195405314838Z/summary.json`. Todas as verificações finais de integridade/FK passaram. Rate limit desativado apenas nos filhos do benchmark, CSRF mantido; não mede comportamento sob limite de tentativas.

Falha do soak: GET `/pagina-inicial`, cliente reportou HTTP 0/timeout de aproximadamente 10 segundos, em 19:59:06 UTC. Log Gunicorn não mostra traceback correspondente; SIGTERM ao término foi encerramento do runner, não demonstra causa do timeout anterior. Causa ainda não isolada; não atribuir com certeza a lock, rede ou host. Repetir em janela controlada com tempos por requisição redigidos e amostras de recursos, preservando este resultado negativo.
