# Deploy acadêmico no PythonAnywhere

Este roteiro publica o UniVet como demonstração acadêmica gratuita, usando apenas dados fictícios e SQLite persistente dentro do diretório da aplicação. Não use dados reais, Neon ou qualquer plano pago neste deploy.

O plano Free do PythonAnywhere oferece um web app com um worker, espaço e CPU limitados, além de expiração periódica da conta/site conforme as regras atuais da plataforma; isso é suficiente para uma avaliação acadêmica temporária, não para operação clínica. O subdomínio `SEU_USUARIO.pythonanywhere.com` recebe HTTPS do próprio PythonAnywhere.

## 1. Código e ambiente no console Bash

Substitua `SEU_USUARIO` pelo seu usuário do PythonAnywhere:

```bash
cd ~
git clone https://github.com/bugijo/Projeto-Integrador---UniVet.git UniVet
cd ~/UniVet
git checkout main

python3.11 -m venv ~/.virtualenvs/univet-demo
source ~/.virtualenvs/univet-demo/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

mkdir -p ~/UniVet/data
export UNIVET_ENV=demo
export DEMO_DATABASE_URL="sqlite:////home/SEU_USUARIO/UniVet/data/univet-demo.db"
python init_db.py --demo
```

O arquivo `data/univet-demo.db` fica fora de diretórios temporários e não deve ser adicionado ao Git. O comando `init_db.py --demo` é executado uma vez para criar o schema e inserir o seed fictício. Não execute `init_db.py` a cada request ou reload.

Verificação antes de criar o Web App:

```bash
UNIVET_ENV=demo \
DEMO_DATABASE_URL="sqlite:////home/SEU_USUARIO/UniVet/data/univet-demo.db" \
python -c "import sqlite3; c=sqlite3.connect('data/univet-demo.db'); print(c.execute(\"SELECT environment FROM univet_environment WHERE id=1\").fetchone()[0]); print(c.execute('SELECT COUNT(*) FROM usuarios').fetchone()[0])"
```

O resultado esperado é `demo` e pelo menos `2` usuários fictícios.

## 2. Chave de sessão fora do repositório

Gere uma chave localmente no console, sem registrá-la no Git:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Copie o resultado apenas para o arquivo WSGI privado do seu Web App. Não coloque a chave neste repositório, no README ou em logs.

## 3. Criar o Web App

Na aba **Web** do PythonAnywhere:

1. Clique em **Add a new web app**.
2. Escolha **Manual configuration**.
3. Escolha Python 3.11, compatível com o virtualenv usado acima.
4. Informe o virtualenv `~/.virtualenvs/univet-demo`.
5. Adicione o mapeamento de arquivos estáticos:
   - URL: `/static/`
   - Directory: `/home/SEU_USUARIO/UniVet/static`

## 4. Configurar o WSGI

Abra o arquivo WSGI indicado na aba **Web** e use este conteúdo, substituindo `SEU_USUARIO` e colando a chave gerada somente nesse arquivo privado:

```python
import os
import sys

PROJECT_DIR = "/home/SEU_USUARIO/UniVet"
os.environ["UNIVET_PROJECT_DIR"] = PROJECT_DIR
os.environ["UNIVET_ENV"] = "demo"
os.environ["DEMO_DATABASE_URL"] = f"sqlite:///{PROJECT_DIR}/data/univet-demo.db"
os.environ["SECRET_KEY"] = "COLE_A_CHAVE_GERADA_SOMENTE_AQUI"

if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

from pythonanywhere_wsgi import application
```

O arquivo `pythonanywhere_wsgi.py` do repositório valida o diretório, configura o SQLite demo e importa `app` como `application`. Ele não cria nem recria o banco durante o import.

Ative **Force HTTPS** na seção Security da aba Web. O entrypoint WSGI usa cookies `Secure`, portanto o login publicado deve ser acessado por HTTPS.

Clique em **Reload** depois de salvar o WSGI e após cada atualização do código.

## 5. Verificação online

Substitua `SEU_USUARIO`:

```bash
curl -i https://SEU_USUARIO.pythonanywhere.com/health
curl -i https://SEU_USUARIO.pythonanywhere.com/login
curl -i https://SEU_USUARIO.pythonanywhere.com/
```

Depois faça login com a conta fictícia `admin` criada pelo seed e demonstre tutores, animais, veterinários, serviços, consultas, histórico, estoque, categorias, fornecedores, produtos, lotes, entradas, saídas, FEFO, relatórios, API, CSV e logout.

Se houver erro 500, consulte os arquivos **Error log** e **Server log** na aba Web. Nunca copie secrets ou connection strings para os logs ou para uma issue.

## Limites conhecidos

- SQLite é adequado aqui somente para a demonstração acadêmica de um worker gratuito.
- Não usar concorrência pesada, dados reais ou operação clínica.
- O seed é fictício e idempotente; não deve ser usado para resetar o banco durante o funcionamento.
- A conta demo e os dados podem ser removidos manualmente apagando apenas `data/univet-demo.db` no console, caso seja necessário recomeçar a demonstração.

Referências oficiais: [Flask no PythonAnywhere](https://help.pythonanywhere.com/pages/Flask), [mapeamento de arquivos estáticos](https://help.pythonanywhere.com/pages/StaticFiles/), [recursos de contas Free](https://help.pythonanywhere.com/pages/FreeAccountsFeatures/) e [HTTPS](https://help.pythonanywhere.com/pages/HTTPSSetup).
