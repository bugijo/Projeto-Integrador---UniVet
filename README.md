# UniVet

Sistema de gestao veterinaria desenvolvido para o Projeto Integrador I da UNIVESP.

## Visao geral

O UniVet organiza a rotina da recepcao da Clinica Veterinaria Fernanda Calixto com foco em cadastro, agenda e praticidade.

## Funcionalidades do MVP

- acesso por codigo da proprietaria
- pagina inicial com agenda do dia
- cadastro de tutores com CPF validado
- cadastro de animais vinculados a tutores
- calendario mensal de consultas
- agenda detalhada por dia

## Tecnologias utilizadas

- Python 3
- Flask
- SQLite
- HTML5
- CSS3
- Jinja2

## Estrutura do projeto

```text
UniVet/
|-- app.py
|-- init_db.py
|-- run_server.py
|-- banco.db
|-- static/
|   |-- logo-clinica.jpg
|   |-- style.css
|-- templates/
|   |-- base.html
|   |-- login.html
|   |-- pagina_inicial.html
|   |-- tutores/
|   |   |-- form.html
|   |   |-- lista.html
|   |-- pets/
|   |   |-- form.html
|   |   |-- lista.html
|   |-- consultas/
|       |-- dia.html
|       |-- form.html
|       |-- lista.html
```

## Como executar

1. Instale as dependencias:

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

- Codigo de acesso: `246810`

## Regras implementadas

- a pagina interna exige autenticacao por codigo
- todo tutor precisa de CPF valido
- todo animal precisa estar vinculado a um tutor
- toda consulta precisa estar vinculada a um animal
- um tutor com animais nao pode ser excluido
- um animal com consultas nao pode ser excluido
