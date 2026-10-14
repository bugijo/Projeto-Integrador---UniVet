# UniVet — Projeto Integrador II

Aplicação acadêmica de gestão veterinária para avaliação da faculdade. O UniVet é uma demonstração funcional com dados exclusivamente fictícios; não está liberado para dados reais de uma clínica.

## Visão geral

O UniVet demonstra cadastros, agenda, prontuário clínico, operação de estoque e controles de segurança em um ambiente acadêmico isolado. A referência visual da clínica não significa que este repositório esteja pronto para uso clínico real.

## Funcionalidades do UniVet 2.0

- autenticação com dois perfis autorizados
- página inicial com agenda do dia
- cadastro de tutores com CPF validado
- cadastro de animais vinculados a tutores
- calendário mensal de consultas
- agenda detalhada por dia
- histórico clínico do paciente a partir da consulta
- auditoria de alterações por registro
- dashboard operacional de estoque
- cadastro de produtos, categorias e fornecedores
- controle de lotes, validade e entradas
- saídas manuais e uso de produtos em consultas
- rastreabilidade de movimentações, estornos e FEFO
- alertas de estoque mínimo e vencimento
- análise simples de consumo e sugestão transparente de reposição
- dashboard com indicadores de valor, consumo e reposição
- filtros e paginação em listagens de estoque
- exportação CSV de movimentações, posição e consumo
- API autenticada para resumo, produtos e movimentações de estoque

## Tecnologias utilizadas

- Python 3
- Flask
- PostgreSQL compatível com Neon para o ambiente online/demo
- SQLite para desenvolvimento e testes locais isolados
- HTML5
- CSS3
- Jinja2
- unittest
- JavaScript e SVG nativos, sem bibliotecas externas obrigatórias

## Estrutura do projeto

```text
UniVet/
|-- app.py
|-- init_db.py
|-- run_server.py
|-- banco.db
|-- tests/
|   |-- test_app.py
|   |-- test_estoque.py
|-- estoque/
|   |-- schema.py
|   |-- services.py
|-- docs/
|   |-- relatorio-parcial-rascunho.md
|   |-- evolucao-pi1-para-pi2.md
|   |-- analise-propostas-estoque.md
|   |-- integracao-propostas-estoque.md
|-- .github/
|   |-- workflows/
|       |-- ci.yml
|-- static/
|   |-- logo-clinica.jpg
|   |-- style.css
|-- templates/
|   |-- base.html
|   |-- historico.html
|   |-- login.html
|   |-- pagina_inicial.html
|   |-- consultas/
|   |   |-- dia.html
|   |   |-- form.html
|   |   |-- historico.html
|   |   |-- lista.html
|   |-- pets/
|   |   |-- form.html
|   |   |-- lista.html
|   |-- tutores/
|   |   |-- form.html
|   |   |-- lista.html
```

## Como executar

1. Instale as dependências:

```bash
pip install -r requirements.txt
```

No ambiente deste projeto, também é possível preparar um ambiente isolado com `uv`:

```bash
uv venv .venv
uv pip install --python .venv/bin/python -r requirements.txt
```

2. Crie ou atualize o banco:

```bash
python init_db.py
```

3. Rode o sistema:

```bash
python run_server.py
```

4. Abra no navegador:

```text
http://127.0.0.1:5000
```

## Demonstração acadêmica

O banco demo deve ser configurado com `UNIVET_ENV=demo` e uma `DEMO_DATABASE_URL` apontando para um PostgreSQL separado, como o projeto gratuito `univet-demo` no Neon. O seed opt-in de `init_db.py --demo` cria dados fictícios de tutores, animais, veterinários, serviços, consultas, categorias, fornecedores, produtos, lotes e movimentações.

A conta acadêmica é o usuário fictício `admin`, com nome “Administrador de testes”. A senha deve ser informada somente no ambiente local/demo ou pelo responsável pela apresentação; ela não é documentada neste repositório.

## Testes

```bash
python -m unittest discover -s tests -v
```

O projeto não depende de APIs pagas, serviços com cobrança por requisição ou bibliotecas comerciais. O ambiente online/demo deve usar PostgreSQL externo persistente; SQLite permanece restrito ao desenvolvimento e aos testes locais. Hospedagem gratuita pode suspender o serviço por limites da plataforma, portanto disponibilidade online precisa ser verificada antes da avaliação.

## Avaliação acadêmica

Fluxo recomendado: entrar pelo login, abrir o dashboard e demonstrar tutores, animais, veterinários, serviços, agendamentos, consultas e histórico; depois navegar pelo estoque para cadastrar categoria, fornecedor, produto, lote, entrada, saída, FEFO, baixa automática, alertas, relatórios, API, CSV e logout.

Para executar localmente com dados fictícios:

```bash
export UNIVET_ENV=demo
export DEMO_DATABASE_URL='<URL Neon com sslmode=verify-full, sslrootcert=system e channel_binding=require>'
python init_db.py --demo
gunicorn -w 2 -b 127.0.0.1:5000 app:app
```

Nunca publique os valores das variáveis de ambiente, use dados reais ou apresente o projeto como pronto para uma clínica.

Para publicar a demonstração no PythonAnywhere, siga [docs/deploy-pythonanywhere.md](docs/deploy-pythonanywhere.md).

## Rotas principais do estoque

- `/estoque`: dashboard operacional;
- `/estoque/produtos`: produtos, busca, filtros e paginação;
- `/estoque/lotes`: lotes, validade, fornecedor e ajustes;
- `/estoque/movimentacoes`: histórico, filtros e estornos;
- `/estoque/relatorios`: consumo, reposição e indicadores;
- `/estoque/exportar/*.csv`: exportações locais;
- `/api/estoque/resumo`, `/api/estoque/produtos` e `/api/estoque/movimentacoes`: API autenticada.

## Cobertura de testes

A suíte automatizada cobre autenticação, módulos clínicos, estoque, FEFO, validade, estoque negativo, estornos, integração com consultas, concorrência, filtros, paginação, CSV, API, PostgreSQL, migrations, CSRF, sessões e parâmetros inválidos. O PostgreSQL é executado somente em banco descartável local quando o teste opt-in é ativado.

## Pipeline GitHub

O workflow `.github/workflows/ci.yml` executa:

- inicialização do banco
- validação de sintaxe
- testes automatizados
- disparo opcional de deploy via `RENDER_DEPLOY_HOOK_URL`
- smoke test opcional via `PRODUCTION_BASE_URL`

## Regras implementadas

- o seed acadêmico cria somente contas fictícias de demonstração
- toda senha é salva com hash seguro
- todo tutor precisa de CPF válido
- todo animal precisa estar vinculado a um tutor
- toda consulta precisa estar vinculada a um animal
- um tutor com animais não pode ser excluído
- um animal com consultas não pode ser excluído
- ao excluir um veterinário com consultas vinculadas, o sistema redistribui os atendimentos para outro profissional disponível
