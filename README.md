# UniVet

Sistema de gestão veterinária desenvolvido para o Projeto Integrador I da UNIVESP.

## Visão geral

O UniVet organiza a rotina da recepção da Clínica Veterinária Fernanda Calixto com foco em cadastro, agenda e praticidade.

## Funcionalidades do MVP

- acesso por código da proprietária
- página inicial com agenda do dia
- cadastro de tutores com CPF validado
- cadastro de animais vinculados a tutores
- calendário mensal de consultas
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

- Código de acesso: `246810`

## Regras implementadas

- a página interna exige autenticação por código
- todo tutor precisa de CPF válido
- todo animal precisa estar vinculado a um tutor
- toda consulta precisa estar vinculada a um animal
- um tutor com animais não pode ser excluído
- um animal com consultas não pode ser excluído
