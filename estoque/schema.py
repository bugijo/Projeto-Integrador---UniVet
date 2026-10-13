"""Schema incremental das tabelas do módulo de estoque."""


def criar_tabelas_estoque(connection):
    """Cria as tabelas do estoque sem modificar as tabelas legadas do PI I."""
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS categorias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL UNIQUE,
            descricao TEXT,
            ativo INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1)),
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS fornecedores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL UNIQUE,
            documento TEXT,
            telefone TEXT,
            email TEXT,
            endereco TEXT,
            ativo INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1)),
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS produtos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            codigo TEXT UNIQUE,
            tipo TEXT NOT NULL CHECK (tipo IN ('Medicamento', 'Vacina', 'Material', 'Produto')),
            categoria_id INTEGER,
            unidade_medida TEXT NOT NULL DEFAULT 'unidade',
            estoque_minimo REAL NOT NULL DEFAULT 0 CHECK (estoque_minimo >= 0),
            ativo INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1)),
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (categoria_id) REFERENCES categorias(id) ON DELETE SET NULL
        );

        CREATE TABLE IF NOT EXISTS lotes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            produto_id INTEGER NOT NULL,
            fornecedor_id INTEGER,
            numero_lote TEXT NOT NULL,
            quantidade_inicial REAL NOT NULL CHECK (quantidade_inicial > 0),
            quantidade_atual REAL NOT NULL CHECK (quantidade_atual >= 0),
            validade TEXT,
            valor_compra_unitario REAL NOT NULL DEFAULT 0 CHECK (valor_compra_unitario >= 0),
            data_entrada TEXT NOT NULL,
            ativo INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1)),
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (produto_id) REFERENCES produtos(id) ON DELETE RESTRICT,
            FOREIGN KEY (fornecedor_id) REFERENCES fornecedores(id) ON DELETE SET NULL,
            UNIQUE (produto_id, numero_lote)
        );

        CREATE TABLE IF NOT EXISTS movimentacoes_estoque (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            produto_id INTEGER NOT NULL,
            lote_id INTEGER NOT NULL,
            tipo TEXT NOT NULL CHECK (tipo IN ('Entrada', 'Saída', 'Ajuste', 'Estorno')),
            quantidade REAL NOT NULL CHECK (quantidade > 0),
            quantidade_variacao REAL,
            motivo TEXT NOT NULL,
            consulta_id INTEGER,
            usuario_id INTEGER,
            movimentacao_origem_id INTEGER,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (produto_id) REFERENCES produtos(id) ON DELETE RESTRICT,
            FOREIGN KEY (lote_id) REFERENCES lotes(id) ON DELETE RESTRICT,
            FOREIGN KEY (consulta_id) REFERENCES consultas(id) ON DELETE SET NULL,
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE SET NULL,
            FOREIGN KEY (movimentacao_origem_id) REFERENCES movimentacoes_estoque(id) ON DELETE SET NULL
        );

        CREATE TABLE IF NOT EXISTS itens_consulta (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            consulta_id INTEGER NOT NULL,
            produto_id INTEGER NOT NULL,
            lote_id INTEGER NOT NULL,
            quantidade REAL NOT NULL CHECK (quantidade > 0),
            movimentacao_id INTEGER,
            usuario_id INTEGER,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (consulta_id) REFERENCES consultas(id) ON DELETE RESTRICT,
            FOREIGN KEY (produto_id) REFERENCES produtos(id) ON DELETE RESTRICT,
            FOREIGN KEY (lote_id) REFERENCES lotes(id) ON DELETE RESTRICT,
            FOREIGN KEY (movimentacao_id) REFERENCES movimentacoes_estoque(id) ON DELETE SET NULL,
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE SET NULL
        );

        CREATE INDEX IF NOT EXISTS idx_produtos_categoria ON produtos(categoria_id);
        CREATE INDEX IF NOT EXISTS idx_produtos_tipo_ativo ON produtos(tipo, ativo);
        CREATE INDEX IF NOT EXISTS idx_lotes_produto_validade ON lotes(produto_id, validade, quantidade_atual);
        CREATE INDEX IF NOT EXISTS idx_lotes_fornecedor ON lotes(fornecedor_id);
        CREATE INDEX IF NOT EXISTS idx_movimentacoes_produto_data ON movimentacoes_estoque(produto_id, criado_em);
        CREATE INDEX IF NOT EXISTS idx_movimentacoes_lote ON movimentacoes_estoque(lote_id);
        CREATE UNIQUE INDEX IF NOT EXISTS idx_estorno_unico_origem
            ON movimentacoes_estoque(movimentacao_origem_id)
            WHERE tipo = 'Estorno' AND movimentacao_origem_id IS NOT NULL;
        CREATE INDEX IF NOT EXISTS idx_movimentacoes_consulta ON movimentacoes_estoque(consulta_id);
        CREATE INDEX IF NOT EXISTS idx_itens_consulta ON itens_consulta(consulta_id);
        """
    )
    colunas = {item[1] for item in connection.execute("PRAGMA table_info(movimentacoes_estoque)").fetchall()}
    if "quantidade_variacao" not in colunas:
        connection.execute("ALTER TABLE movimentacoes_estoque ADD COLUMN quantidade_variacao REAL")
    connection.execute(
        """
        UPDATE movimentacoes_estoque
        SET quantidade_variacao = CASE tipo WHEN 'Saída' THEN -quantidade ELSE quantidade END
        WHERE quantidade_variacao IS NULL
        """
    )

    migracoes = {
        "produtos": [("margem_lucro_percentual", "REAL NOT NULL DEFAULT 30")],
        "lotes": [("valor_venda_sugerido_unitario", "REAL NOT NULL DEFAULT 0")],
        "movimentacoes_estoque": [
            ("valor_unitario_sugerido", "REAL"),
            ("valor_unitario_praticado", "REAL"),
        ],
        "itens_consulta": [
            ("valor_unitario_sugerido", "REAL"),
            ("valor_unitario_praticado", "REAL"),
        ],
    }
    for tabela, colunas_novas in migracoes.items():
        existentes = {item[1] for item in connection.execute(f"PRAGMA table_info({tabela})").fetchall()}
        for coluna, definicao in colunas_novas:
            if coluna not in existentes:
                connection.execute(f"ALTER TABLE {tabela} ADD COLUMN {coluna} {definicao}")

    connection.execute(
        """
        UPDATE lotes
        SET valor_venda_sugerido_unitario = ROUND(
            valor_compra_unitario * (1 + COALESCE((SELECT margem_lucro_percentual FROM produtos WHERE produtos.id = lotes.produto_id), 30) / 100),
            2
        )
        WHERE valor_venda_sugerido_unitario IS NULL OR valor_venda_sugerido_unitario = 0
        """
    )
