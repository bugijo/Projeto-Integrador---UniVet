---
name: univet-testing
description: Planejar e executar testes do UniVet, reproduções de regressão, segurança, concorrência ou carga local, com banco descartável e evidências resumidas.
---
# Testes

`tests/test_app.py` testa HTTP com Flask test client; `tests/test_estoque.py` testa serviços e integridade. Antes de testes adicionais, confirme isolamento: altere AMBOS `app.DATABASE` e `init_db.DATABASE` para diretório temporário; limpe caches de referência e restaure globals ao terminar. Nunca use o banco local da clínica nem o banco online.
Comandos na raiz:
- Caso: `PYTHONPATH=tests .venv/bin/python -m unittest test_estoque.EstoqueServicesTests.test_saida_nao_permite_estoque_negativo -v`.
- Módulo: `PYTHONPATH=tests .venv/bin/python -m unittest test_estoque -v`.
- Suíte/checkpoints: comando e política no `AGENTS.md`.
Salve saída longa em artefatos ignorados; informe contagem, duração e falhas. Não confunda teste de caracterização que confirma falha com aprovação de segurança.
Regressão: login, agenda/prontuário, CSV/API e entradas/saídas/FEFO/validade/preços/estorno. Smoke local inclui anonimato e acesso autorizado usando dados fictícios. Smoke online é leitura leve e não prova versão implantada.
Concorrência: conexões independentes, sincronização de threads, limite/timeout, disputa de saída, estorno duplicado e ajuste; conferir saldo, quantidade de movimentos e rollback. Testes sequenciais não demonstram concorrência.
Carga somente em ambiente local/descartável, com volume e duração limitados, coleta de erros/latência, interrupção se saturar. Registrar hardware/dados e limites: não extrapolar para capacidade de produção.
Aceite: suíte completa verde, regressões cobertas, nenhuma violação de integridade, falhas de segurança críticas/altas resolvidas ou bloqueio explícito de produção. Metas de desempenho e limites de concorrência devem ser definidos antes de homologação.
