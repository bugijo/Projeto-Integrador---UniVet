# UniVet

Sistema de gestão veterinária desenvolvido para o Projeto Integrador da UNIVESP e continuado no Projeto Integrador II.

## Visão geral

O UniVet organiza a rotina da Clínica Veterinária Fernanda Calixto com foco em cadastros, agenda, prontuário clínico e operação diária.

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
- SQLite
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

## Credenciais iniciais

- Administrador de testes: `admin / 123456`
- Dra. Fernanda Calixto: `fernanda.calixto / Fer123`

## Testes

```bash
python -m unittest discover -s tests -v
```

O projeto não depende de APIs pagas, serviços com cobrança por requisição ou bibliotecas comerciais. O protótipo utiliza Flask, SQLite, JavaScript, CSS e SVG próprios. O deploy descrito em `render.yaml` continua sujeito às limitações de persistência do SQLite em hospedagens gratuitas.

## Rotas principais do estoque

- `/estoque`: dashboard operacional;
- `/estoque/produtos`: produtos, busca, filtros e paginação;
- `/estoque/lotes`: lotes, validade, fornecedor e ajustes;
- `/estoque/movimentacoes`: histórico, filtros e estornos;
- `/estoque/relatorios`: consumo, reposição e indicadores;
- `/estoque/exportar/*.csv`: exportações locais;
- `/api/estoque/resumo`, `/api/estoque/produtos` e `/api/estoque/movimentacoes`: API autenticada.

## Cobertura de testes

A suíte atual possui 27 testes automatizados cobrindo autenticação, módulos clínicos, estoque, FEFO, validade, estoque negativo, estornos, integração com consultas, filtros, paginação, CSV, API e parâmetros inválidos.

## Pipeline GitHub

O workflow `.github/workflows/ci.yml` executa:

- inicialização do banco
- validação de sintaxe
- testes automatizados
- disparo opcional de deploy via `RENDER_DEPLOY_HOOK_URL`
- smoke test opcional via `PRODUCTION_BASE_URL`

## Regras implementadas

- apenas os usuários `admin` e `fernanda.calixto` permanecem ativos no banco
- toda senha é salva com hash seguro
- todo tutor precisa de CPF válido
- todo animal precisa estar vinculado a um tutor
- toda consulta precisa estar vinculada a um animal
- um tutor com animais não pode ser excluído
- um animal com consultas não pode ser excluído
- ao excluir um veterinário com consultas vinculadas, o sistema redistribui os atendimentos para outro profissional disponível
