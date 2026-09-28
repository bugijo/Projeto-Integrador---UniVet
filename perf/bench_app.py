"""Entrada WSGI/seed exclusiva do snapshot temporário criado por run.py."""
import os
from pathlib import Path
import sys
from werkzeug.security import generate_password_hash

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
    # Contas isoladas do gerador: evitam que o login compartilhado acione
    # legitimamente o rate limit durante a medição de concorrência.
    connection = init_db.connect(init_db.DATABASE)
    try:
        cursor = connection.cursor()
        for index in range(50):
            init_db.criar_ou_atualizar_usuario(
                cursor,
                f"bench_qa_{index:02d}",
                f"Conta QA local {index:02d}",
                "admin",
                "QA-Benchmark-Local-2026!",
            )
        connection.commit()
    finally:
        connection.close()
