from pathlib import Path
import sqlite3

from werkzeug.security import generate_password_hash


BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "banco.db"


def garantir_coluna(cursor, tabela, coluna, definicao):
    """Adiciona uma coluna nova quando o banco ja existe e precisa evoluir."""
    colunas = cursor.execute(f"PRAGMA table_info({tabela})").fetchall()
    nomes_colunas = [coluna_existente[1] for coluna_existente in colunas]

    if coluna not in nomes_colunas:
        cursor.execute(f"ALTER TABLE {tabela} ADD COLUMN {coluna} {definicao}")


def init_db():
    """Cria as tabelas principais do sistema e um usuario inicial de teste."""
    connection = sqlite3.connect(DATABASE)
    cursor = connection.cursor()

    cursor.execute("PRAGMA foreign_keys = ON;")

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            login TEXT NOT NULL UNIQUE,
            senha_hash TEXT NOT NULL
        );
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS tutores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            telefone TEXT NOT NULL
        );
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS pets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            especie TEXT NOT NULL,
            raca TEXT NOT NULL,
            tutor_id INTEGER NOT NULL,
            historico TEXT,
            FOREIGN KEY (tutor_id) REFERENCES tutores (id)
        );
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS consultas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data_hora TEXT NOT NULL,
            pet_id INTEGER NOT NULL,
            observacoes TEXT,
            status TEXT NOT NULL CHECK (status IN ('Agendada', 'Concluida', 'Cancelada')),
            FOREIGN KEY (pet_id) REFERENCES pets (id)
        );
        """
    )

    # Campos extras opcionais para aproximar o sistema do formulario pedido no briefing.
    garantir_coluna(cursor, "tutores", "endereco", "TEXT")
    garantir_coluna(cursor, "pets", "idade", "TEXT")

    usuario_existente = cursor.execute(
        "SELECT id, senha_hash FROM usuarios WHERE login = ?;",
        ("admin",),
    ).fetchone()

    if not usuario_existente:
        cursor.execute(
            """
            INSERT INTO usuarios (login, senha_hash)
            VALUES (?, ?);
            """,
            ("admin", generate_password_hash("123456")),
        )
    elif not str(usuario_existente[1]).startswith("scrypt:"):
        cursor.execute(
            """
            UPDATE usuarios
            SET senha_hash = ?
            WHERE id = ?;
            """,
            (generate_password_hash("123456"), usuario_existente[0]),
        )

    connection.commit()
    connection.close()

    print("Banco de dados inicializado com sucesso.")
    print("Usuario padrao: admin")
    print("Senha padrao: 123456")


if __name__ == "__main__":
    init_db()
