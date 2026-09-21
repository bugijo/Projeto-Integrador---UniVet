"""Entrada WSGI/seed exclusiva do snapshot temporário criado por run.py."""
import os
from pathlib import Path
import sys

root = Path(os.environ["UNIVET_BENCH_ROOT"]).resolve()
database = Path(os.environ["UNIVET_DATABASE"]).resolve()
if (not (root / "isolated-benchmark").is_file() or root not in database.parents
        or os.environ.get("UNIVET_ENV") != "development"):
    raise RuntimeError("Configuração fora do benchmark isolado")

sys.path.insert(0, str(root / "source"))
import init_db  # noqa: E402
import app as application  # noqa: E402

# Falhar antes de qualquer seed/requisição se a aplicação ignorar UNIVET_DATABASE.
if Path(application.DATABASE).resolve() != database or Path(init_db.DATABASE).resolve() != database:
    raise RuntimeError("app e init_db precisam respeitar UNIVET_DATABASE antes da carga")

app = application.app

if __name__ == "__main__":
    if database.exists():
        raise RuntimeError("Seed permitido somente em banco novo descartável")
    init_db.init_db(seed_demo=True)
