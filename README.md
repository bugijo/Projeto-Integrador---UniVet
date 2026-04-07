# UniVet

Sistema de gestão veterinária desenvolvido para o Projeto Integrador I da UNIVESP.

## Visão geral

O UniVet organiza a rotina da Clínica Veterinária Fernanda Calixto com foco em cadastros, agenda, prontuário clínico e operação diária.

## Funcionalidades do MVP

- autenticação com dois perfis autorizados
- página inicial com agenda do dia
- cadastro de tutores com CPF validado
- cadastro de animais vinculados a tutores
- calendário mensal de consultas
- agenda detalhada por dia
- histórico clínico do paciente a partir da consulta
- auditoria de alterações por registro

## Tecnologias utilizadas

- Python 3
- Flask
- SQLite
- HTML5
- CSS3
- Jinja2
- unittest

## Estrutura do projeto

```text
UniVet/
|-- app.py
|-- init_db.py
|-- run_server.py
|-- banco.db
|-- tests/
|   |-- test_app.py
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
