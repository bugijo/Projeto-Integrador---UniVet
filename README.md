# UniVet

Sistema de Gestao Veterinaria desenvolvido para o Projeto Integrador I da UNIVESP.

## Visao geral

O UniVet foi planejado como um MVP para apoiar a rotina da recepcao da clinica veterinaria, com foco em organizacao de dados e praticidade de uso.

## Funcionalidades do MVP

- login da proprietaria
- dashboard com agenda do dia
- cadastro de tutores
- cadastro de pets vinculados a tutores
- cadastro e acompanhamento de consultas

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
|-- banco.db
|-- static/
|   |-- style.css
|-- templates/
|   |-- base.html
|   |-- dashboard.html
|   |-- login.html
|   |-- tutores/
|   |   |-- form.html
|   |   |-- lista.html
|   |-- pets/
|   |   |-- form.html
|   |   |-- lista.html
|   |-- consultas/
|       |-- form.html
|       |-- lista.html
```

## Modelagem do banco

### Tabela usuarios

- `id`
- `login`
- `senha_hash`

### Tabela tutores

- `id`
- `nome`
- `telefone`
- `endereco`

### Tabela pets

- `id`
- `nome`
- `especie`
- `raca`
- `idade`
- `tutor_id`
- `historico`

### Tabela consultas

- `id`
- `data_hora`
- `pet_id`
- `observacoes`
- `status`

## Como executar

1. Instale a dependencia principal:

```bash
pip install flask
```

2. Crie ou atualize o banco de dados:

```bash
python init_db.py
```

3. Inicie o sistema:

```bash
python app.py
```

4. Abra no navegador:

```text
http://127.0.0.1:5000
```

## Usuario inicial para testes

- Login: `admin`
- Senha: `123456`

## Regras de negocio implementadas

- o login e obrigatorio para acessar as paginas internas
- todo pet deve estar vinculado a um tutor
- uma consulta sempre precisa estar vinculada a um pet
- um tutor com pets cadastrados nao pode ser excluido
- um pet com consultas cadastradas nao pode ser excluido

## Observacoes academicas

- O codigo foi escrito com foco em simplicidade e leitura, para facilitar a apresentacao do grupo.
- As rotas do Flask e as funcoes principais possuem comentarios curtos.
- O projeto prioriza clareza antes de sofisticacao, o que ajuda alunos de primeiro semestre a entenderem o fluxo completo.
