"""Consultas e regras de negócio do módulo de estoque."""

from datetime import datetime


TIPOS_PRODUTO = ("Medicamento", "Vacina", "Material", "Produto")
TIPOS_MOVIMENTACAO = ("Entrada", "Saída", "Ajuste", "Estorno")


class EstoqueError(Exception):
    """Erro de regra de negócio apresentado ao usuário."""


class EstoqueInsuficiente(EstoqueError):
    """Indica que a saída solicitada excede o estoque disponível."""


def _agora():
    return datetime.now().strftime("%Y-%m-%dT%H:%M")


def _quantidade(valor):
    try:
        valor = float(valor)
    except (TypeError, ValueError):
        raise EstoqueError("Informe uma quantidade válida.")
    if valor <= 0:
        raise EstoqueError("A quantidade deve ser maior que zero.")
    return valor


def _valor_praticado(valor, sugerido=0):
    """Normaliza o preço praticado; quando omitido, usa a sugestão do lote."""
    if valor is None or str(valor).strip() == "":
        return round(float(sugerido or 0), 2)
    try:
        valor = float(str(valor).replace(",", "."))
    except (TypeError, ValueError) as exc:
        raise EstoqueError("Informe um valor de venda válido.") from exc
    if valor < 0:
        raise EstoqueError("O valor de venda não pode ser negativo.")
    return round(valor, 2)


def _data_valida(valor, nome="data"):
    if not valor:
        return None
    try:
        datetime.strptime(valor, "%Y-%m-%d")
    except ValueError as exc:
        raise EstoqueError(f"Informe uma {nome} válida.") from exc
    return valor


def listar_categorias(connection, somente_ativas=False, busca=""):
    sql = "SELECT * FROM categorias WHERE 1 = 1"
    params = []
    if somente_ativas:
        sql += " AND ativo = 1"
    if busca:
        sql += " AND (nome LIKE ? OR coalesce(descricao, '') LIKE ?)"
        filtro = f"%{busca}%"
        params.extend((filtro, filtro))
    return connection.execute(sql + " ORDER BY nome ASC", params).fetchall()


def listar_fornecedores(connection, somente_ativos=False, busca="", filtros=None, status=""):
    filtros = filtros or {}
    sql = "SELECT * FROM fornecedores WHERE 1 = 1"
    params = []
    if somente_ativos:
        sql += " AND ativo = 1"
    if status in ("ativo", "inativo"):
        sql += " AND ativo = ?"
        params.append(1 if status == "ativo" else 0)
    if busca:
        sql += " AND (nome LIKE ? OR coalesce(documento, '') LIKE ? OR coalesce(email, '') LIKE ?)"
        filtro = f"%{busca}%"
        params.extend((filtro, filtro, filtro))
    return _paginacao(connection, sql, params, filtros, " ORDER BY nome ASC")


def _paginacao(connection, sql, params, filtros, ordem, chave="id"):
    """Executa uma consulta paginada somente quando o chamador solicita."""
    if not filtros.get("paginado"):
        return connection.execute(sql + ordem, params).fetchall()
    try:
        pagina = max(1, int(filtros.get("pagina", 1)))
    except (TypeError, ValueError):
        pagina = 1
    try:
        por_pagina = min(100, max(1, int(filtros.get("por_pagina", 20))))
    except (TypeError, ValueError):
        por_pagina = 20
    total = connection.execute(f"SELECT COUNT(*) FROM ({sql}) AS consulta", params).fetchone()[0]
    dados = connection.execute(
        sql + ordem + " LIMIT ? OFFSET ?", [*params, por_pagina, (pagina - 1) * por_pagina]
    ).fetchall()
    return {
        "itens": dados,
        "pagina": pagina,
        "por_pagina": por_pagina,
        "total": total,
        "total_paginas": max(1, (total + por_pagina - 1) // por_pagina),
    }


def listar_produtos(connection, filtros=None):
    filtros = filtros or {}
    sql = """
        SELECT produtos.*, categorias.nome AS categoria_nome,
               COALESCE(SUM(CASE WHEN lotes.ativo = 1 THEN lotes.quantidade_atual ELSE 0 END), 0) AS estoque_total,
               COALESCE(SUM(CASE WHEN lotes.ativo = 1 THEN lotes.quantidade_atual * lotes.valor_compra_unitario ELSE 0 END), 0) AS valor_estoque,
               COUNT(DISTINCT CASE WHEN lotes.ativo = 1 THEN lotes.id END) AS total_lotes,
               MIN(CASE WHEN lotes.ativo = 1 AND lotes.quantidade_atual > 0 AND lotes.validade IS NOT NULL THEN lotes.validade END) AS proxima_validade,
               COALESCE(MIN(CASE WHEN lotes.ativo = 1 AND lotes.quantidade_atual > 0 THEN lotes.valor_venda_sugerido_unitario END), 0) AS valor_venda_sugerido
        FROM produtos
        LEFT JOIN categorias ON categorias.id = produtos.categoria_id
        LEFT JOIN lotes ON lotes.produto_id = produtos.id
        WHERE 1 = 1
    """
    params = []
    if filtros.get("busca"):
        sql += " AND (produtos.nome LIKE ? OR coalesce(produtos.codigo, '') LIKE ?)"
        termo = f"%{filtros['busca']}%"
        params.extend((termo, termo))
    if filtros.get("tipo") in TIPOS_PRODUTO:
        sql += " AND produtos.tipo = ?"
        params.append(filtros["tipo"])
    if filtros.get("categoria_id"):
        sql += " AND produtos.categoria_id = ?"
        params.append(filtros["categoria_id"])
    if filtros.get("situacao") == "baixo":
        sql += " AND produtos.estoque_minimo > 0"
    if filtros.get("somente_ativos"):
        sql += " AND produtos.ativo = 1"
    sql += " GROUP BY produtos.id"
    if filtros.get("situacao") == "baixo":
        sql += " HAVING estoque_total < produtos.estoque_minimo"
    return _paginacao(connection, sql, params, filtros, " ORDER BY produtos.ativo DESC, produtos.nome ASC")


def buscar_produto(connection, produto_id):
    return connection.execute(
        """
        SELECT produtos.*, categorias.nome AS categoria_nome,
               COALESCE(SUM(CASE WHEN lotes.ativo = 1 THEN lotes.quantidade_atual ELSE 0 END), 0) AS estoque_total,
               COUNT(DISTINCT CASE WHEN lotes.ativo = 1 THEN lotes.id END) AS total_lotes,
               COALESCE(MIN(CASE WHEN lotes.ativo = 1 AND lotes.quantidade_atual > 0 THEN lotes.valor_venda_sugerido_unitario END), 0) AS valor_venda_sugerido
        FROM produtos
        LEFT JOIN categorias ON categorias.id = produtos.categoria_id
        LEFT JOIN lotes ON lotes.produto_id = produtos.id
        WHERE produtos.id = ?
        GROUP BY produtos.id
        """,
        (produto_id,),
    ).fetchone()


def listar_lotes(connection, filtros=None):
    filtros = filtros or {}
    sql = """
        SELECT lotes.*, produtos.nome AS produto_nome, produtos.codigo AS produto_codigo,
               produtos.unidade_medida, produtos.margem_lucro_percentual, fornecedores.nome AS fornecedor_nome
        FROM lotes
        INNER JOIN produtos ON produtos.id = lotes.produto_id
        LEFT JOIN fornecedores ON fornecedores.id = lotes.fornecedor_id
        WHERE 1 = 1
    """
    params = []
    if filtros.get("produto_id"):
        sql += " AND lotes.produto_id = ?"
        params.append(filtros["produto_id"])
    if filtros.get("fornecedor_id"):
        sql += " AND lotes.fornecedor_id = ?"
        params.append(filtros["fornecedor_id"])
    if filtros.get("proximos"):
        sql += " AND lotes.validade IS NOT NULL AND date(lotes.validade) <= date('now', '+30 day') AND date(lotes.validade) >= date('now')"
    if filtros.get("vencidos"):
        sql += " AND lotes.validade IS NOT NULL AND date(lotes.validade) < date('now') AND lotes.quantidade_atual > 0"
    return _paginacao(
        connection,
        sql,
        params,
        filtros,
        " ORDER BY CASE WHEN lotes.quantidade_atual > 0 AND lotes.validade IS NOT NULL THEN 0 ELSE 1 END, date(lotes.validade), lotes.id DESC",
    )


def listar_movimentacoes(connection, filtros=None, limite=None):
    filtros = filtros or {}
    sql = """
        SELECT movimentacoes_estoque.*, produtos.nome AS produto_nome,
               lotes.numero_lote, usuarios.nome AS usuario_nome,
               consultas.data_hora AS consulta_data_hora, pets.nome AS pet_nome
        FROM movimentacoes_estoque
        INNER JOIN produtos ON produtos.id = movimentacoes_estoque.produto_id
        INNER JOIN lotes ON lotes.id = movimentacoes_estoque.lote_id
        LEFT JOIN usuarios ON usuarios.id = movimentacoes_estoque.usuario_id
        LEFT JOIN consultas ON consultas.id = movimentacoes_estoque.consulta_id
        LEFT JOIN pets ON pets.id = consultas.pet_id
        WHERE 1 = 1
    """
    params = []
    if filtros.get("produto_id"):
        sql += " AND movimentacoes_estoque.produto_id = ?"
        params.append(filtros["produto_id"])
    if filtros.get("usuario_id"):
        sql += " AND movimentacoes_estoque.usuario_id = ?"
        params.append(filtros["usuario_id"])
    if filtros.get("consulta_id"):
        sql += " AND movimentacoes_estoque.consulta_id = ?"
        params.append(filtros["consulta_id"])
    if filtros.get("tipo") in TIPOS_MOVIMENTACAO:
        sql += " AND movimentacoes_estoque.tipo = ?"
        params.append(filtros["tipo"])
    if filtros.get("data_inicio"):
        sql += " AND date(movimentacoes_estoque.criado_em) >= date(?)"
        params.append(filtros["data_inicio"])
    if filtros.get("data_fim"):
        sql += " AND date(movimentacoes_estoque.criado_em) <= date(?)"
        params.append(filtros["data_fim"])
    sql += " ORDER BY movimentacoes_estoque.criado_em DESC, movimentacoes_estoque.id DESC"
    if filtros.get("paginado"):
        return _paginacao(connection, sql.removesuffix(" ORDER BY movimentacoes_estoque.criado_em DESC, movimentacoes_estoque.id DESC"), params, filtros, " ORDER BY movimentacoes_estoque.criado_em DESC, movimentacoes_estoque.id DESC")
    if limite:
        sql += " LIMIT ?"
        params.append(limite)
    return connection.execute(sql, params).fetchall()


def resumo_estoque(connection):
    produtos = connection.execute("SELECT COUNT(*) FROM produtos WHERE ativo = 1").fetchone()[0]
    estoque = connection.execute("SELECT COALESCE(SUM(quantidade_atual), 0) FROM lotes WHERE ativo = 1").fetchone()[0]
    valor_estoque = connection.execute("SELECT COALESCE(SUM(quantidade_atual * valor_compra_unitario), 0) FROM lotes WHERE ativo = 1").fetchone()[0]
    baixo = connection.execute(
        """
        SELECT COUNT(*) FROM (
            SELECT produtos.id
            FROM produtos LEFT JOIN lotes ON lotes.produto_id = produtos.id AND lotes.ativo = 1
            WHERE produtos.ativo = 1
            GROUP BY produtos.id
            HAVING COALESCE(SUM(lotes.quantidade_atual), 0) < produtos.estoque_minimo
               AND produtos.estoque_minimo > 0
        )
        """
    ).fetchone()[0]
    vencendo = connection.execute(
        """
        SELECT COUNT(*) FROM lotes
        WHERE ativo = 1 AND quantidade_atual > 0 AND validade IS NOT NULL
          AND date(validade) BETWEEN date('now') AND date('now', '+30 day')
        """
    ).fetchone()[0]
    return {"produtos": produtos, "unidades": estoque, "valor_estoque": float(valor_estoque or 0), "baixo": baixo, "vencendo": vencendo}


def registrar_entrada(connection, produto_id, fornecedor_id, numero_lote, quantidade, validade, valor, usuario_id, motivo="Compra"):
    if not numero_lote or not str(numero_lote).strip():
        raise EstoqueError("Informe o número do lote.")
    quantidade = _quantidade(quantidade)
    validade = _data_valida(validade, "validade")
    try:
        valor = float(valor or 0)
    except (TypeError, ValueError):
        raise EstoqueError("Informe um valor de compra válido.")
    if valor < 0:
        raise EstoqueError("O valor de compra não pode ser negativo.")
    produto = connection.execute("SELECT margem_lucro_percentual FROM produtos WHERE id = ?", (produto_id,)).fetchone()
    if not produto:
        raise EstoqueError("Produto não encontrado.")
    valor_sugerido = round(valor * (1 + float(produto["margem_lucro_percentual"] or 0) / 100), 2)
    agora = _agora()
    try:
        connection.execute("BEGIN IMMEDIATE")
        cursor = connection.execute(
            """
            INSERT INTO lotes (produto_id, fornecedor_id, numero_lote, quantidade_inicial, quantidade_atual, validade, valor_compra_unitario, valor_venda_sugerido_unitario, data_entrada)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (produto_id, fornecedor_id or None, numero_lote.strip(), quantidade, quantidade, validade, valor, valor_sugerido, agora[:10]),
        )
        lote_id = cursor.lastrowid
        movement = connection.execute(
            """
            INSERT INTO movimentacoes_estoque (produto_id, lote_id, tipo, quantidade, quantidade_variacao, valor_unitario_sugerido, motivo, usuario_id, criado_em)
            VALUES (?, ?, 'Entrada', ?, ?, ?, ?, ?, ?)
            """,
            (produto_id, lote_id, quantidade, quantidade, valor_sugerido, motivo.strip() or "Compra", usuario_id, agora),
        )
        connection.commit()
        return lote_id, movement.lastrowid
    except Exception:
        connection.rollback()
        raise


def registrar_saida_fefo(connection, produto_id, quantidade, usuario_id, motivo="Uso em atendimento", consulta_id=None, valor_unitario_praticado=None):
    quantidade = _quantidade(quantidade)
    hoje = datetime.now().strftime("%Y-%m-%d")
    try:
        connection.execute("BEGIN IMMEDIATE")
        lotes = connection.execute(
            """
            SELECT * FROM lotes
            WHERE produto_id = ? AND ativo = 1 AND quantidade_atual > 0
              AND (validade IS NULL OR validade >= ?)
            ORDER BY CASE WHEN validade IS NULL THEN 1 ELSE 0 END, validade ASC, id ASC
            """,
            (produto_id, hoje),
        ).fetchall()
        disponivel = sum(float(lote["quantidade_atual"]) for lote in lotes)
        if disponivel < quantidade:
            raise EstoqueInsuficiente(
                f"Estoque insuficiente. Disponível: {disponivel:g}; solicitado: {quantidade:g}."
            )
        restante = quantidade
        alocacoes = []
        for lote in lotes:
            usada = min(restante, float(lote["quantidade_atual"]))
            if usada <= 0:
                continue
            atualizado = connection.execute(
                "UPDATE lotes SET quantidade_atual = quantidade_atual - ? WHERE id = ? AND quantidade_atual >= ?",
                (usada, lote["id"], usada),
            )
            if atualizado.rowcount != 1:
                raise EstoqueError("O estoque mudou durante a operação. Tente novamente.")
            movement = connection.execute(
                """
                INSERT INTO movimentacoes_estoque (produto_id, lote_id, tipo, quantidade, quantidade_variacao, valor_unitario_sugerido, valor_unitario_praticado, motivo, consulta_id, usuario_id)
                VALUES (?, ?, 'Saída', ?, ?, ?, ?, ?, ?, ?)
                """,
                (produto_id, lote["id"], usada, -usada, lote["valor_venda_sugerido_unitario"], _valor_praticado(valor_unitario_praticado, lote["valor_venda_sugerido_unitario"]), motivo.strip() or "Uso em atendimento", consulta_id, usuario_id),
            )
            alocacoes.append({"lote_id": lote["id"], "quantidade": usada, "movimentacao_id": movement.lastrowid, "numero_lote": lote["numero_lote"], "valor_unitario_sugerido": lote["valor_venda_sugerido_unitario"], "valor_unitario_praticado": _valor_praticado(valor_unitario_praticado, lote["valor_venda_sugerido_unitario"])})
            restante -= usada
            if restante <= 0.000001:
                break
        connection.commit()
        return alocacoes
    except Exception:
        connection.rollback()
        raise


def registrar_uso_consulta(connection, consulta_id, produto_id, quantidade, usuario_id, motivo="Uso em atendimento", valor_unitario_praticado=None):
    """Baixa produtos por FEFO e vincula todas as parcelas à consulta em uma transação."""
    quantidade = _quantidade(quantidade)
    consulta = connection.execute("SELECT id FROM consultas WHERE id = ?", (consulta_id,)).fetchone()
    if not consulta:
        raise EstoqueError("Consulta não encontrada.")
    hoje = datetime.now().strftime("%Y-%m-%d")
    try:
        connection.execute("BEGIN IMMEDIATE")
        lotes = connection.execute(
            """
            SELECT * FROM lotes
            WHERE produto_id = ? AND ativo = 1 AND quantidade_atual > 0
              AND (validade IS NULL OR validade >= ?)
            ORDER BY CASE WHEN validade IS NULL THEN 1 ELSE 0 END, validade ASC, id ASC
            """,
            (produto_id, hoje),
        ).fetchall()
        disponivel = sum(float(lote["quantidade_atual"]) for lote in lotes)
        if disponivel < quantidade:
            raise EstoqueInsuficiente(
                f"Estoque insuficiente. Disponível: {disponivel:g}; solicitado: {quantidade:g}."
            )
        restante = quantidade
        itens = []
        for lote in lotes:
            usada = min(restante, float(lote["quantidade_atual"]))
            if usada <= 0:
                continue
            atualizado = connection.execute(
                "UPDATE lotes SET quantidade_atual = quantidade_atual - ? WHERE id = ? AND quantidade_atual >= ?",
                (usada, lote["id"], usada),
            )
            if atualizado.rowcount != 1:
                raise EstoqueError("O estoque mudou durante a operação. Tente novamente.")
            movement = connection.execute(
                """
                INSERT INTO movimentacoes_estoque (produto_id, lote_id, tipo, quantidade, quantidade_variacao, valor_unitario_sugerido, valor_unitario_praticado, motivo, consulta_id, usuario_id)
                VALUES (?, ?, 'Saída', ?, ?, ?, ?, ?, ?, ?)
                """,
                (produto_id, lote["id"], usada, -usada, lote["valor_venda_sugerido_unitario"], _valor_praticado(valor_unitario_praticado, lote["valor_venda_sugerido_unitario"]), motivo.strip() or "Uso em atendimento", consulta_id, usuario_id),
            )
            item = connection.execute(
                """
                INSERT INTO itens_consulta (consulta_id, produto_id, lote_id, quantidade, valor_unitario_sugerido, valor_unitario_praticado, movimentacao_id, usuario_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (consulta_id, produto_id, lote["id"], usada, lote["valor_venda_sugerido_unitario"], _valor_praticado(valor_unitario_praticado, lote["valor_venda_sugerido_unitario"]), movement.lastrowid, usuario_id),
            )
            itens.append({"id": item.lastrowid, "lote_id": lote["id"], "numero_lote": lote["numero_lote"], "quantidade": usada, "valor_unitario_sugerido": lote["valor_venda_sugerido_unitario"], "valor_unitario_praticado": _valor_praticado(valor_unitario_praticado, lote["valor_venda_sugerido_unitario"]), "movimentacao_id": movement.lastrowid})
            restante -= usada
            if restante <= 0.000001:
                break
        connection.commit()
        return itens
    except Exception:
        connection.rollback()
        raise


def registrar_ajuste(connection, lote_id, nova_quantidade, usuario_id, motivo):
    try:
        nova_quantidade = float(nova_quantidade)
    except (TypeError, ValueError):
        raise EstoqueError("Informe uma quantidade válida.")
    if nova_quantidade < 0:
        raise EstoqueError("A quantidade ajustada não pode ser negativa.")
    lote = connection.execute("SELECT * FROM lotes WHERE id = ?", (lote_id,)).fetchone()
    if not lote:
        raise EstoqueError("Lote não encontrado.")
    diferenca = nova_quantidade - float(lote["quantidade_atual"])
    if abs(diferenca) < 0.000001:
        raise EstoqueError("A nova quantidade é igual ao saldo atual.")
    descricao = motivo.strip() if motivo and motivo.strip() else "Ajuste de inventário"
    descricao = f"{descricao} ({'aumento' if diferenca > 0 else 'redução'})"
    try:
        connection.execute("BEGIN IMMEDIATE")
        atualizado = connection.execute(
            "UPDATE lotes SET quantidade_atual = ? WHERE id = ? AND quantidade_atual + ? >= 0",
            (nova_quantidade, lote_id, diferenca),
        )
        if atualizado.rowcount != 1:
            raise EstoqueError("Não foi possível aplicar o ajuste.")
        movimento = connection.execute(
            """
            INSERT INTO movimentacoes_estoque (produto_id, lote_id, tipo, quantidade, quantidade_variacao, valor_unitario_sugerido, valor_unitario_praticado, motivo, usuario_id)
            VALUES (?, ?, 'Ajuste', ?, ?, ?, ?, ?, ?)
            """,
            (lote["produto_id"], lote_id, abs(diferenca), diferenca, lote["valor_venda_sugerido_unitario"], lote["valor_venda_sugerido_unitario"], descricao, usuario_id),
        )
        connection.commit()
        return movimento.lastrowid
    except Exception:
        connection.rollback()
        raise


def listar_itens_consulta(connection, consulta_id):
    return connection.execute(
        """
        SELECT itens_consulta.*, produtos.nome AS produto_nome, produtos.unidade_medida,
               lotes.numero_lote, movimentacoes_estoque.criado_em,
               movimentacoes_estoque.quantidade * COALESCE(movimentacoes_estoque.valor_unitario_praticado, 0) AS valor_total
        FROM itens_consulta
        INNER JOIN produtos ON produtos.id = itens_consulta.produto_id
        INNER JOIN lotes ON lotes.id = itens_consulta.lote_id
        LEFT JOIN movimentacoes_estoque ON movimentacoes_estoque.id = itens_consulta.movimentacao_id
        WHERE itens_consulta.consulta_id = ?
        ORDER BY itens_consulta.id DESC
        """,
        (consulta_id,),
    ).fetchall()


def registrar_estorno(connection, movimentacao_id, usuario_id, motivo="Estorno"):
    origem = connection.execute("SELECT * FROM movimentacoes_estoque WHERE id = ?", (movimentacao_id,)).fetchone()
    if not origem:
        raise EstoqueError("Movimentação não encontrada.")
    if origem["tipo"] not in ("Saída", "Ajuste"):
        raise EstoqueError("Somente saídas e ajustes podem ser estornados.")
    ja_estornada = connection.execute(
        "SELECT 1 FROM movimentacoes_estoque WHERE movimentacao_origem_id = ? AND tipo = 'Estorno'",
        (movimentacao_id,),
    ).fetchone()
    if ja_estornada:
        raise EstoqueError("Esta movimentação já possui um estorno.")
    variacao_origem = origem["quantidade_variacao"]
    if variacao_origem is None:
        variacao_origem = -origem["quantidade"] if origem["tipo"] == "Saída" else origem["quantidade"]
    variacao_estorno = -float(variacao_origem)
    try:
        connection.execute("BEGIN IMMEDIATE")
        atualizado = connection.execute(
            "UPDATE lotes SET quantidade_atual = quantidade_atual + ? WHERE id = ? AND quantidade_atual + ? >= 0",
            (variacao_estorno, origem["lote_id"], variacao_estorno),
        )
        if atualizado.rowcount != 1:
            raise EstoqueError("O estorno resultaria em estoque negativo.")
        estorno = connection.execute(
            """
            INSERT INTO movimentacoes_estoque (produto_id, lote_id, tipo, quantidade, quantidade_variacao, valor_unitario_sugerido, valor_unitario_praticado, motivo, consulta_id, usuario_id, movimentacao_origem_id)
            VALUES (?, ?, 'Estorno', ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (origem["produto_id"], origem["lote_id"], abs(variacao_estorno), variacao_estorno, origem["valor_unitario_sugerido"], origem["valor_unitario_praticado"], motivo.strip() or "Estorno", origem["consulta_id"], usuario_id, movimentacao_id),
        )
        connection.commit()
        return estorno.lastrowid
    except Exception:
        connection.rollback()
        raise


def consumo_por_produto(connection, produto_id, dias=30):
    dados = connection.execute(
        """
        SELECT COALESCE(SUM(quantidade), 0) AS quantidade,
               COUNT(DISTINCT date(criado_em)) AS dias_com_uso
        FROM movimentacoes_estoque
        WHERE produto_id = ? AND tipo = 'Saída'
          AND date(criado_em) >= date('now', ?)
        """,
        (produto_id, f"-{int(dias)} day"),
    ).fetchone()
    quantidade = float(dados["quantidade"] or 0)
    medio_diario = quantidade / dias if quantidade else 0
    return {"quantidade": quantidade, "medio_diario": medio_diario, "dias": dias}


def historico_consumo_diario(connection, produto_id, dias=7):
    registros = connection.execute(
        """
        SELECT date(criado_em) AS dia, COALESCE(SUM(quantidade), 0) AS quantidade
        FROM movimentacoes_estoque
        WHERE produto_id = ? AND tipo = 'Saída'
          AND date(criado_em) >= date('now', ?)
        GROUP BY date(criado_em)
        ORDER BY dia ASC
        """,
        (produto_id, f"-{int(dias) - 1} day"),
    ).fetchall()
    por_dia = {item["dia"]: float(item["quantidade"]) for item in registros}
    hoje = datetime.now().date()
    return [{"dia": (hoje.fromordinal(hoje.toordinal() - (dias - 1 - indice))).strftime("%d/%m"), "quantidade": por_dia.get((hoje.fromordinal(hoje.toordinal() - (dias - 1 - indice))).isoformat(), 0)} for indice in range(dias)]


def relatorio_consumo(connection, dias=30, produto_id=None, categoria_id=None):
    sql = """
        SELECT produtos.id, produtos.nome, produtos.tipo, produtos.unidade_medida,
               categorias.nome AS categoria_nome,
               COALESCE(SUM(CASE WHEN movimentacoes_estoque.tipo = 'Saída' THEN movimentacoes_estoque.quantidade ELSE 0 END), 0) AS consumo,
               COALESCE((SELECT SUM(lotes.quantidade_atual) FROM lotes WHERE lotes.produto_id = produtos.id AND lotes.ativo = 1), 0) AS estoque_atual,
               COALESCE((SELECT SUM(lotes.quantidade_atual * lotes.valor_compra_unitario) FROM lotes WHERE lotes.produto_id = produtos.id AND lotes.ativo = 1), 0) AS valor_estoque
        FROM produtos
        LEFT JOIN categorias ON categorias.id = produtos.categoria_id
        LEFT JOIN movimentacoes_estoque ON movimentacoes_estoque.produto_id = produtos.id
          AND date(movimentacoes_estoque.criado_em) >= date('now', ?)
        WHERE produtos.ativo = 1
    """
    params = [f"-{int(dias)} day"]
    if produto_id:
        sql += " AND produtos.id = ?"
        params.append(produto_id)
    if categoria_id:
        sql += " AND produtos.categoria_id = ?"
        params.append(categoria_id)
    sql += " GROUP BY produtos.id ORDER BY consumo DESC, produtos.nome ASC"
    return connection.execute(sql, params).fetchall()


def sugestao_reposicao(produto, consumo, semanas_cobertura=4):
    """Aplica uma regra transparente: mínimo + quatro semanas de consumo médio."""
    if not consumo["quantidade"]:
        return {"disponivel": False, "mensagem": "Sem histórico suficiente para sugerir reposição."}
    consumo_semanal = consumo["medio_diario"] * 7
    alvo = max(float(produto["estoque_minimo"]), consumo_semanal * semanas_cobertura)
    quantidade = max(0, alvo - float(produto["estoque_total"]))
    return {
        "disponivel": quantidade > 0,
        "quantidade": quantidade,
        "consumo_semanal": consumo_semanal,
        "mensagem": "Reposição recomendada." if quantidade > 0 else "Estoque suficiente para a regra atual.",
    }
