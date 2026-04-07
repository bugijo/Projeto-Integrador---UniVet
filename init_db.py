from pathlib import Path
import sqlite3

from werkzeug.security import generate_password_hash


BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "banco.db"

ESPECIES = [
    ("Cao", None), ("Gato", None), ("Ave", None), ("Reptil", None), ("Roedor", None),
    ("Peixe", None), ("Equino", None), ("Bovino", None), ("Suino", None),
]

RACAS = {
    "Cao": ["Labrador Retriever", "Golden Retriever", "Bulldog Frances", "Poodle", "Yorkshire Terrier", "Beagle", "Rottweiler", "Pastor Alemao", "SRD", "Shih Tzu"],
    "Gato": ["Persa", "Siames", "Maine Coon", "Sphynx", "Ragdoll", "British Shorthair", "Bengal", "Scottish Fold", "Angora", "SRD"],
    "Ave": ["Calopsita", "Periquito", "Canario", "Papagaio", "Cacatua", "Agapornis"],
    "Reptil": ["Iguana", "Jiboia", "Tartaruga Tigre D'agua", "Gecko Leopardo", "Teiu"],
    "Roedor": ["Hamster Sirio", "Porquinho da India", "Chinchila", "Twister", "Gerbil"],
    "Peixe": ["Betta", "Kinguio", "Guppy", "Acará Bandeira"],
    "Equino": ["Mangalarga", "Quarto de Milha", "Crioulo"],
    "Bovino": ["Nelore", "Girolando", "Holandes"],
    "Suino": ["Mini Pig", "Landrace", "Large White"],
}

SERVICOS = [
    ("Vacinacao", 20),
    ("Consulta de rotina", 20),
    ("Retorno clinico", 20),
    ("Exame laboratorial", 40),
    ("Ultrassom", 40),
    ("Internacao", 60),
    ("Cirurgia", 120),
]

VETERINARIOS = ["Dra. Fernanda Calixto", "Dr. Rafael Moreira"]

USUARIOS_PADRAO = [
    ("admin", "Administrador de testes", "admin", "123456"),
    ("fernanda.calixto", "Dra. Fernanda Calixto", "veterinaria", "Fer123"),
]


def garantir_coluna(cursor, tabela, coluna, definicao):
    colunas = cursor.execute(f"PRAGMA table_info({tabela})").fetchall()
    nomes = [coluna_existente[1] for coluna_existente in colunas]
    if coluna not in nomes:
        cursor.execute(f"ALTER TABLE {tabela} ADD COLUMN {coluna} {definicao}")


def criar_ou_atualizar_usuario(cursor, login, nome, perfil, senha):
    usuario = cursor.execute("SELECT id FROM usuarios WHERE login = ?", (login,)).fetchone()
    senha_hash = generate_password_hash(senha)
    if usuario:
        cursor.execute(
            """
            UPDATE usuarios
            SET nome = ?, perfil = ?, senha_hash = ?, ativo = 1
            WHERE id = ?
            """,
            (nome, perfil, senha_hash, usuario[0]),
        )
        return usuario[0]
    cursor.execute(
        """
        INSERT INTO usuarios (login, nome, perfil, senha_hash, ativo)
        VALUES (?, ?, ?, ?, 1)
        """,
        (login, nome, perfil, senha_hash),
    )
    return cursor.lastrowid


def init_db():
    connection = sqlite3.connect(DATABASE)
    cursor = connection.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")

    cursor.execute("CREATE TABLE IF NOT EXISTS usuarios (id INTEGER PRIMARY KEY AUTOINCREMENT, login TEXT NOT NULL UNIQUE, senha_hash TEXT NOT NULL)")
    cursor.execute("CREATE TABLE IF NOT EXISTS tutores (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT NOT NULL, telefone TEXT NOT NULL)")
    cursor.execute("CREATE TABLE IF NOT EXISTS especies (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT NOT NULL UNIQUE, parent_id INTEGER, FOREIGN KEY(parent_id) REFERENCES especies(id))")
    cursor.execute("CREATE TABLE IF NOT EXISTS racas (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT NOT NULL, especie_id INTEGER NOT NULL, UNIQUE(nome, especie_id), FOREIGN KEY(especie_id) REFERENCES especies(id))")
    cursor.execute("CREATE TABLE IF NOT EXISTS veterinarios (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT NOT NULL UNIQUE)")
    cursor.execute("CREATE TABLE IF NOT EXISTS servicos (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT NOT NULL UNIQUE, duracao_minutos INTEGER NOT NULL CHECK(duracao_minutos >= 20))")
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS historico_alteracoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entidade TEXT NOT NULL,
            registro_id INTEGER NOT NULL,
            acao TEXT NOT NULL,
            usuario_nome TEXT NOT NULL,
            dados_json TEXT NOT NULL,
            criado_em TEXT NOT NULL
        )
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
        )
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
        )
        """
    )

    for tabela, coluna, definicao in [
        ("usuarios", "access_code_hash", "TEXT"),
        ("usuarios", "nome", "TEXT"),
        ("usuarios", "perfil", "TEXT DEFAULT 'veterinaria'"),
        ("usuarios", "ativo", "INTEGER DEFAULT 1"),
        ("tutores", "cpf", "TEXT"),
        ("tutores", "endereco", "TEXT"),
        ("pets", "idade", "TEXT"),
        ("pets", "especie_id", "INTEGER"),
        ("pets", "raca_id", "INTEGER"),
        ("consultas", "tipo_consulta", "TEXT DEFAULT 'Consulta de rotina'"),
        ("consultas", "confirmacao_status", "TEXT DEFAULT 'Pendente'"),
        ("consultas", "data_fim", "TEXT"),
        ("consultas", "servico_id", "INTEGER"),
        ("consultas", "duracao_total_minutos", "INTEGER DEFAULT 20"),
        ("consultas", "veterinario_id", "INTEGER"),
        ("consultas", "tipo_atendimento", "TEXT DEFAULT 'Presencial'"),
        ("consultas", "diagnostico", "TEXT"),
        ("consultas", "tratamento", "TEXT"),
        ("consultas", "vacinas", "TEXT"),
    ]:
        garantir_coluna(cursor, tabela, coluna, definicao)

    cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_tutores_cpf ON tutores (cpf)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_historico_entidade_registro ON historico_alteracoes (entidade, registro_id, criado_em)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pets_tutor ON pets (tutor_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_consultas_pet ON consultas (pet_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_consultas_veterinario_periodo ON consultas (veterinario_id, data_hora, data_fim)")

    cursor.executescript(
        """
        DROP TRIGGER IF EXISTS validar_raca_especie_insert;
        DROP TRIGGER IF EXISTS validar_raca_especie_update;
        CREATE TRIGGER validar_raca_especie_insert
        BEFORE INSERT ON pets
        FOR EACH ROW
        WHEN NEW.raca_id IS NOT NULL
             AND (SELECT especie_id FROM racas WHERE id = NEW.raca_id) != NEW.especie_id
        BEGIN
            SELECT RAISE(ABORT, 'Raca nao pertence a especie selecionada');
        END;
        CREATE TRIGGER validar_raca_especie_update
        BEFORE UPDATE ON pets
        FOR EACH ROW
        WHEN NEW.raca_id IS NOT NULL
             AND (SELECT especie_id FROM racas WHERE id = NEW.raca_id) != NEW.especie_id
        BEGIN
            SELECT RAISE(ABORT, 'Raca nao pertence a especie selecionada');
        END;
        """
    )

    for nome, parent_id in ESPECIES:
        cursor.execute("INSERT OR IGNORE INTO especies (nome, parent_id) VALUES (?, ?)", (nome, parent_id))

    especies_map = {row[1]: row[0] for row in cursor.execute("SELECT id, nome FROM especies").fetchall()}
    for especie_nome, racas in RACAS.items():
        especie_id = especies_map[especie_nome]
        for raca in racas:
            cursor.execute("INSERT OR IGNORE INTO racas (nome, especie_id) VALUES (?, ?)", (raca, especie_id))

    for servico, duracao in SERVICOS:
        cursor.execute("INSERT OR IGNORE INTO servicos (nome, duracao_minutos) VALUES (?, ?)", (servico, duracao))

    for veterinario in VETERINARIOS:
        cursor.execute("INSERT OR IGNORE INTO veterinarios (nome) VALUES (?)", (veterinario,))

    for especie_nome, especie_id in especies_map.items():
        cursor.execute("UPDATE pets SET especie_id = ? WHERE especie_id IS NULL AND lower(especie) = lower(?)", (especie_id, especie_nome))
        for raca_id, raca_nome in cursor.execute("SELECT id, nome FROM racas WHERE especie_id = ?", (especie_id,)).fetchall():
            cursor.execute(
                "UPDATE pets SET raca_id = ? WHERE raca_id IS NULL AND especie_id = ? AND lower(raca) = lower(?)",
                (raca_id, especie_id, raca_nome),
            )

    ids_autorizados = []
    for login, nome, perfil, senha in USUARIOS_PADRAO:
        ids_autorizados.append(criar_ou_atualizar_usuario(cursor, login, nome, perfil, senha))
    marcadores = ", ".join("?" for _ in ids_autorizados)
    cursor.execute(f"DELETE FROM usuarios WHERE id NOT IN ({marcadores})", ids_autorizados)

    consultas_por_horario = cursor.execute(
        "SELECT data_hora, COUNT(*) FROM consultas GROUP BY data_hora ORDER BY COUNT(*) DESC LIMIT 1"
    ).fetchone()
    max_conflitos = consultas_por_horario[1] if consultas_por_horario else 1
    total_vets = cursor.execute("SELECT COUNT(*) FROM veterinarios").fetchone()[0]
    while total_vets < max_conflitos:
        total_vets += 1
        cursor.execute("INSERT OR IGNORE INTO veterinarios (nome) VALUES (?)", (f"Profissional de agenda {total_vets}",))

    cursor.execute("DROP INDEX IF EXISTS idx_consulta_inicio_vet")
    veterinario_ids = [row[0] for row in cursor.execute("SELECT id FROM veterinarios ORDER BY id ASC").fetchall()]
    grupos_consulta = cursor.execute("SELECT id, data_hora FROM consultas ORDER BY data_hora ASC, id ASC").fetchall()
    distribuicao = {}
    for consulta_id, data_hora in grupos_consulta:
        ordem = distribuicao.get(data_hora, 0)
        veterinario_id = veterinario_ids[ordem % len(veterinario_ids)]
        cursor.execute("UPDATE consultas SET veterinario_id = COALESCE(veterinario_id, ?) WHERE id = ?", (veterinario_id, consulta_id))
        distribuicao[data_hora] = ordem + 1

    default_vet = cursor.execute("SELECT id FROM veterinarios ORDER BY id ASC LIMIT 1").fetchone()
    default_servico = cursor.execute("SELECT id, nome, duracao_minutos FROM servicos ORDER BY id ASC LIMIT 1").fetchone()
    if default_vet:
        cursor.execute("UPDATE consultas SET veterinario_id = COALESCE(veterinario_id, ?) WHERE veterinario_id IS NULL", (default_vet[0],))
    if default_servico:
        cursor.execute(
            """
            UPDATE consultas
            SET servico_id = COALESCE(servico_id, ?),
                tipo_consulta = COALESCE(tipo_consulta, ?),
                duracao_total_minutos = COALESCE(duracao_total_minutos, ?),
                tipo_atendimento = COALESCE(tipo_atendimento, 'Presencial'),
                confirmacao_status = COALESCE(confirmacao_status, 'Pendente'),
                data_fim = COALESCE(data_fim, replace(substr(datetime(data_hora, '+' || ? || ' minutes'), 1, 16), ' ', 'T'))
            WHERE servico_id IS NULL OR data_fim IS NULL
            """,
            (default_servico[0], default_servico[1], default_servico[2], default_servico[2]),
        )

    cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_consulta_inicio_vet ON consultas (veterinario_id, data_hora)")

    connection.commit()
    connection.close()
    print("Banco de dados inicializado com sucesso.")
    print("Logins de desenvolvimento: admin / 123456 e fernanda.calixto / Fer123")


if __name__ == "__main__":
    init_db()
