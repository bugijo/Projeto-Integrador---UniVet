"""Ensaios destrutivos restritos a TemporaryDirectory, com dados fictícios."""

from collections import Counter
from contextlib import closing, redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import sqlite3
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import maintenance


class BackupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="univet-backup-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "ficticio # origem.db"
        self.backup = self.root / "backup.db"
        self.restored = self.root / "restaurado.db"

        # Importação restrita à fixture; nunca importa app. O patch é aplicado
        # antes de inicializar, e restaurado mesmo quando a criação falha.
        import init_db

        with patch.object(init_db, "DATABASE", self.source), redirect_stdout(io.StringIO()):
            init_db.init_db(seed_demo=False)
        with closing(sqlite3.connect(self.source)) as connection, connection:
            connection.execute("PRAGMA foreign_keys = ON")
            tutor = connection.execute(
                "INSERT INTO tutores (nome, telefone) VALUES ('Tutor fictício', '000000000')"
            ).lastrowid
            pet = connection.execute(
                "INSERT INTO pets (nome, especie, raca, tutor_id) VALUES ('Pet fictício', 'Cão', 'SRD', ?)",
                (tutor,),
            ).lastrowid
            consulta = connection.execute(
                "INSERT INTO consultas (data_hora, pet_id, status) VALUES ('2026-09-19T10:00', ?, 'Agendada')",
                (pet,),
            ).lastrowid
            produto = connection.execute(
                "INSERT INTO produtos (nome, codigo, tipo) VALUES ('Produto fictício', 'TEST-BACKUP', 'Material')"
            ).lastrowid
            lote = connection.execute(
                "INSERT INTO lotes (produto_id, numero_lote, quantidade_inicial, quantidade_atual, data_entrada) "
                "VALUES (?, 'LOTE-FICTICIO', 10, 10, '2026-09-19')", (produto,),
            ).lastrowid
            connection.execute(
                "INSERT INTO movimentacoes_estoque "
                "(produto_id, lote_id, tipo, quantidade, quantidade_variacao, motivo, consulta_id) "
                "VALUES (?, ?, 'Entrada', 10, 10, 'Teste fictício', ?)",
                (produto, lote, consulta),
            )

    def snapshot(self, path):
        with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)) as connection:
            schema = connection.execute(
                "SELECT type, name, tbl_name, sql FROM sqlite_schema ORDER BY type, name"
            ).fetchall()
            tables = {}
            for (name,) in connection.execute("SELECT name FROM sqlite_schema WHERE type = 'table'"):
                quoted = '"' + name.replace('"', '""') + '"'
                tables[name] = Counter(connection.execute(f"SELECT * FROM {quoted}").fetchall())
            self.assertEqual(connection.execute("PRAGMA integrity_check").fetchall(), [("ok",)])
            self.assertEqual(connection.execute("PRAGMA foreign_key_check").fetchall(), [])
            return schema, tables

    def test_backup_destroy_tempfile_restore_all_tables(self):
        expected = self.snapshot(self.source)
        for name in ("tutores", "pets", "consultas", "produtos", "lotes", "movimentacoes_estoque"):
            self.assertTrue(expected[1][name], name)
        result = maintenance.backup_database(self.source, self.backup)
        self.assertEqual(self.snapshot(self.backup), expected)
        self.assertEqual(result["sha256"], hashlib.sha256(self.backup.read_bytes()).hexdigest())
        self.assertEqual(self.source.parent, Path(self.temp.name))
        self.source.unlink()  # SOMENTE este banco fictício dentro do tempfile.
        self.assertFalse(self.source.exists())
        before = self.backup.read_bytes()
        self.backup.chmod(0o400)
        maintenance.restore_database(self.backup, self.source)
        self.assertEqual(self.snapshot(self.source), expected)
        self.assertEqual(self.backup.read_bytes(), before)
        self.assertEqual(stat.S_IMODE(self.source.stat().st_mode), 0o600)

    def test_permissions_and_source_unchanged(self):
        before = self.source.read_bytes()
        maintenance.backup_database(self.source, self.backup)
        self.assertEqual(stat.S_IMODE(self.backup.stat().st_mode), 0o600)
        maintenance.restore_database(self.backup, self.restored)
        self.assertEqual(stat.S_IMODE(self.restored.stat().st_mode), 0o600)
        self.assertEqual(self.source.read_bytes(), before)

    def test_existing_targets_and_aliases_never_overwritten(self):
        before = self.source.read_bytes()
        link = self.root / "link.db"
        link.symlink_to(self.source)
        dangling = self.root / "dangling.db"
        dangling.symlink_to(self.root / "absent.db")
        hardlink = self.root / "hardlink.db"
        hardlink.hardlink_to(self.source)
        existing = self.root / "existing.db"
        existing.write_bytes(b"preservar")
        for operation in (maintenance.backup_database, maintenance.restore_database):
            for target in (self.source, link, dangling, hardlink, existing, self.root):
                with self.subTest(operation=operation.__name__, target=target.name):
                    with self.assertRaises(FileExistsError):
                        operation(self.source, target)
        self.assertEqual(self.source.read_bytes(), before)
        self.assertEqual(existing.read_bytes(), b"preservar")
        self.assertTrue(dangling.is_symlink())

    def test_missing_empty_corrupt_sources_do_not_publish(self):
        empty = self.root / "empty.db"
        empty.touch()
        corrupt = self.root / "corrupt.db"
        corrupt.write_bytes(b"not a SQLite database")
        for operation in (maintenance.backup_database, maintenance.restore_database):
            for source in (self.root / "missing.db", empty, corrupt, self.root):
                with self.subTest(operation=operation.__name__, source=source.name):
                    with self.assertRaises((ValueError, sqlite3.DatabaseError)):
                        operation(source, self.backup)
                    self.assertFalse(self.backup.exists())
        self.assertFalse((self.root / "missing.db").exists())
        self.assertEqual(list(self.root.glob(".univet-backup-*")), [])

    def test_orphaned_foreign_key_rejected(self):
        with closing(sqlite3.connect(self.source)) as connection, connection:
            connection.execute("UPDATE pets SET tutor_id = -999")
        before = self.source.read_bytes()
        for operation in (maintenance.backup_database, maintenance.restore_database):
            with self.assertRaisesRegex(ValueError, "foreign_key_check"):
                operation(self.source, self.backup)
            self.assertFalse(self.backup.exists())
        self.assertEqual(self.source.read_bytes(), before)

    def test_integrity_check_failure_does_not_publish(self):
        with closing(sqlite3.connect(self.source)) as connection, connection:
            connection.execute("PRAGMA ignore_check_constraints = ON")
            connection.execute("UPDATE lotes SET quantidade_atual = -1")
        for operation in (maintenance.backup_database, maintenance.restore_database):
            with self.assertRaisesRegex(ValueError, "integrity_check"):
                operation(self.source, self.backup)
            self.assertFalse(self.backup.exists())

    def test_locked_source_times_out_without_publishing(self):
        with closing(sqlite3.connect(self.source)) as writer:
            # WAL permite leitores durante escrita; este caso testa bloqueio real em DELETE.
            writer.execute('PRAGMA journal_mode=DELETE')
            writer.execute("BEGIN EXCLUSIVE")
            try:
                with self.assertRaises(TimeoutError):
                    maintenance._copy_database(self.source, self.backup, timeout=0.05)
            finally:
                writer.rollback()
        self.assertFalse(self.backup.exists())
        self.assertEqual(list(self.root.glob(".univet-backup-*")), [])

    def test_wal_committed_snapshot_excludes_pending_transaction(self):
        with closing(sqlite3.connect(self.source)) as writer:
            self.assertEqual(writer.execute("PRAGMA journal_mode=WAL").fetchone()[0], "wal")
            writer.execute("PRAGMA wal_autocheckpoint=0")
            writer.execute("INSERT INTO tutores (nome, telefone) VALUES ('Commit fictício WAL', '000')")
            writer.commit()
            expected = self.snapshot(self.source)
            writer.execute("INSERT INTO tutores (nome, telefone) VALUES ('Não confirmado', '000')")
            self.assertGreater(Path(str(self.source) + "-wal").stat().st_size, 0)
            maintenance.backup_database(self.source, self.backup)
            writer.rollback()
        self.assertEqual(self.snapshot(self.backup), expected)
        maintenance.restore_database(self.backup, self.restored)
        self.assertEqual(self.snapshot(self.restored), expected)
        self.assertFalse(Path(str(self.backup) + "-wal").exists())

    def test_target_created_during_copy_is_preserved(self):
        real_link = maintenance.os.link

        def competing_link(source, destination):
            Path(destination).write_bytes(b"criado por outro processo")
            real_link(source, destination)

        with patch.object(maintenance.os, "link", side_effect=competing_link):
            with self.assertRaises(FileExistsError):
                maintenance.backup_database(self.source, self.backup)
        self.assertEqual(self.backup.read_bytes(), b"criado por outro processo")
        self.assertEqual(list(self.root.glob(".univet-backup-*")), [])

    def test_source_connections_are_read_only(self):
        connect = sqlite3.connect
        readers = []

        def inspect_connection(database, *args, **kwargs):
            connection = connect(database, *args, **kwargs)
            if kwargs.get("uri"):
                readers.append(database)
                with self.assertRaises(sqlite3.OperationalError):
                    connection.execute("CREATE TABLE forbidden_write (id INTEGER)")
            return connection

        with patch.object(maintenance.sqlite3, "connect", side_effect=inspect_connection):
            maintenance.backup_database(self.source, self.backup)
            maintenance.restore_database(self.backup, self.restored)
        self.assertEqual(len(readers), 2)
        self.assertTrue(all(uri.endswith("?mode=ro") for uri in readers))

    def test_cli_help_operations_and_errors_without_application_imports(self):
        script = str(Path(maintenance.__file__).resolve())
        # -I exclui o repo do sys.path: a CLI só precisa da biblioteca padrão.
        for args in (("--help",), ("backup", "--help"), ("restore", "--help")):
            result = subprocess.run([sys.executable, "-I", script, *args],
                                    capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
        for command, source, target in (("backup", self.source, self.backup),
                                         ("restore", self.backup, self.restored)):
            result = subprocess.run([sys.executable, "-I", script, command, str(source), str(target)],
                                    capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["integrity_check"], "ok")
        result = subprocess.run([sys.executable, "-I", script, "restore", str(self.backup), str(self.source)],
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 2)
        self.assertIn("sobrescrita proibida", result.stderr)
        self.assertEqual(self.snapshot(self.source), self.snapshot(self.restored))


if __name__ == "__main__":
    unittest.main()
