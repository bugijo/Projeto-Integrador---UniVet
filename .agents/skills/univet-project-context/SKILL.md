---
name: univet-project-context
description: Recuperar arquitetura e pontos de entrada do UniVet ao planejar mudanças entre módulos ou retomar o projeto; não carregar para tarefas sem dependência da arquitetura.
---
# Contexto técnico

Leia o estado em `docs/current-state.md` e confirme-o com Git. Regras globais estão no `AGENTS.md`.
Flask monolítico em `app.py`: rotas, autenticação por sessão assinada, validação, consultas SQL e renderização Jinja2. `estoque/services.py` concentra entradas, FEFO, uso em consultas, ajustes, estornos e relatórios; `estoque/schema.py` contém schema incremental.
`init_db.py` combina schema, atualização de usuários e dados de demonstração; não é uma migração segura de produção. Banco SQLite `banco.db`, caminho definido separadamente em `app.py` e `init_db.py`; conexões da aplicação ativam foreign keys.
Telas em `templates/`; CSS, JS e imagens em `static/`. Dependências em `requirements.txt`: Flask, Werkzeug, Gunicorn. APIs de estoque reutilizam sessão de navegador.
Execução na raiz: `.venv/bin/python app.py`; WSGI: `.venv/bin/gunicorn -w 2 -b 127.0.0.1:8000 app:app`. Instalação e suíte: `AGENTS.md`; execução seletiva: skill `univet-testing`.
`render.yaml` declara serviço Python free; `.github/workflows/ci.yml` instala, inicializa banco do runner, testa e consulta `/login` via `PRODUCTION_BASE_URL`. Esse smoke não comprova qual commit está no Render. Deploy, persistência e recuperação pertencem à skill `univet-production-ops`.
Domínios: tutores, pets, consultas, condições clínicas, histórico, veterinários, serviços e estoque por lote. Preserve FEFO, saldo não negativo e rastreabilidade; distinguir resultado verificado de intenção documentada.
