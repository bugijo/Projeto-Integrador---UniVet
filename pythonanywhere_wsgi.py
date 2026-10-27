"""Template WSGI para o demo acadêmico no PythonAnywhere.

O banco não é criado durante o import do WSGI. Execute ``init_db.py --demo``
uma vez no console, em um diretório persistente, antes de recarregar o site.
"""

import os
from pathlib import Path
import sys


PROJECT_DIR = Path(
    os.environ.get("UNIVET_PROJECT_DIR", "/home/YOUR_USERNAME/UniVet")
).expanduser().resolve()
if not PROJECT_DIR.is_dir():
    raise RuntimeError(
        "Defina UNIVET_PROJECT_DIR no WSGI para o diretório persistente do UniVet."
    )

os.environ.setdefault("UNIVET_ENV", "demo")
os.environ.setdefault(
    "DEMO_DATABASE_URL",
    f"sqlite:///{PROJECT_DIR / 'data' / 'univet-demo.db'}",
)
os.chdir(PROJECT_DIR)
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from app import app as application  # noqa: E402

# Este entrypoint publicado exige Force HTTPS no painel da hospedagem.
# O servidor HTTP local continua usando app.py e sua configuração própria.
application.config['SESSION_COOKIE_SECURE'] = True
