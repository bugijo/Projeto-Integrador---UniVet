"""Backup e restore locais, sem inicializar ou migrar o banco da aplicação."""

import argparse
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import time


def check_integrity(connection):
    """Rejeita corrupção e referências órfãs sem expor registros clínicos."""
    if connection.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
        raise ValueError("integrity_check falhou; destino não publicado")
    if connection.execute("PRAGMA foreign_key_check").fetchone() is not None:
        raise ValueError("foreign_key_check falhou; destino não publicado")


def _copy_database(source, destination, timeout=30.0):
    source = Path(source).absolute()
    destination = Path(destination).absolute()
    if os.path.lexists(destination):
        raise FileExistsError("Destino já existe; sobrescrita proibida")
    if not source.is_file() or source.stat().st_size == 0:
        raise ValueError("Fonte deve ser um arquivo SQLite existente e não vazio")
    if timeout <= 0:
        raise ValueError("Timeout deve ser positivo")

    deadline = time.monotonic() + timeout

    def progress(status, remaining, total):
        if time.monotonic() > deadline:
            raise TimeoutError("Tempo limite do backup excedido; destino não publicado")

    # O diretório privado fica no mesmo filesystem para publicação atômica por
    # hard link: até uma criação concorrente do destino é recusada, sem overwrite.
    with tempfile.TemporaryDirectory(prefix=".univet-backup-", dir=destination.parent) as tmp:
        staged = Path(tmp) / "validated.sqlite"
        fd = os.open(staged, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        try:
            os.fchmod(fd, 0o600)
        finally:
            os.close(fd)
        with closing(sqlite3.connect(source.as_uri() + "?mode=ro", uri=True,
                                     timeout=timeout)) as reader:
            reader.execute("PRAGMA query_only = ON")
            with closing(sqlite3.connect(staged)) as writer:
                reader.backup(writer, pages=256, progress=progress, sleep=0.05)
                # Consolida eventual WAL herdado em um único arquivo portátil.
                writer.execute("PRAGMA journal_mode = DELETE")
                check_integrity(writer)
        digest = hashlib.sha256()
        with staged.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
            os.fsync(stream.fileno())
        os.link(staged, destination)
        # A limpeza remove apenas a cópia temporária privada criada acima.
    return {
        "destination": str(destination),
        "sha256": digest.hexdigest(),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "integrity_check": "ok",
        "foreign_key_check": "ok",
    }


def backup_database(source, destination):
    """Obtém snapshot consistente de uma fonte read-only para destino novo 0600."""
    return _copy_database(source, destination)


def restore_database(source, destination):
    """Restaura para arquivo inexistente; nunca troca ou exclui banco existente."""
    return _copy_database(source, destination)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Backup/restore SQLite local consistente e validado (arquivo 0600).",
        epilog=("Fonte aberta somente para leitura. Destino deve ser inexistente e seu "
                "diretório deve existir. Guarde backups fora do Git. Restore não troca "
                "o banco em uso. Sucesso: JSON com UTC, SHA-256 e integridade; erro: saída 2."),
    )
    commands = parser.add_subparsers(dest="command", required=True)
    for name, help_text in (("backup", "Criar backup validado"),
                            ("restore", "Restaurar em destino novo")):
        command = commands.add_parser(name, help=help_text, description=help_text)
        command.add_argument("source", type=Path, help="Arquivo SQLite de origem (read-only)")
        command.add_argument("destination", type=Path, help="Novo arquivo; nunca sobrescrito")
    args = parser.parse_args(argv)
    try:
        operation = backup_database if args.command == "backup" else restore_database
        result = operation(args.source, args.destination)
    except (OSError, sqlite3.Error, ValueError) as exc:
        parser.exit(2, f"Erro: {exc}\n")
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
