from calendar import Calendar
import csv
from datetime import datetime, timedelta
from functools import lru_cache
from functools import wraps
import os
from io import StringIO
from pathlib import Path
import json
import sqlite3
import unicodedata

from flask import Flask, Response, flash, g, has_request_context, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash
from security import register_security, start_session, end_session, password_hash
from config import load_settings, verify_database_environment

from estoque.services import (
    EstoqueError,
    EstoqueInsuficiente,
    buscar_produto,
    consumo_por_produto,
    listar_categorias,
    listar_fornecedores,
    historico_consumo_diario,
    listar_lotes,
    listar_itens_consulta,
    listar_movimentacoes,
    listar_produtos,
    relatorio_consumo,
    registrar_entrada,
    registrar_ajuste,
    registrar_estorno,
    registrar_saida_fefo,
    registrar_uso_consulta,
    resumo_estoque,
    sugestao_reposicao,
)


BASE_DIR = Path(__file__).resolve().parent
SETTINGS = load_settings()
DATABASE = SETTINGS.database
STATUSS_CONSULTA = ("Agendada", "Concluida", "Cancelada")
STATUSS_CONFIRMACAO = ("Pendente", "Confirmada", "Nao confirmada")
TIPOS_ATENDIMENTO = ("Presencial", "Domiciliar")
STATUSS_CONDICAO = ("Ativa", "Controlada", "Resolvida")
MESES_PT = {
    1: "Janeiro", 2: "Fevereiro", 3: "Marco", 4: "Abril", 5: "Maio", 6: "Junho",
    7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro",
}
HORARIO_INICIO = 8
HORARIO_FIM = 18
SLOT_MINUTOS = 20
PERFIS_AUTORIZADOS = ("admin", "veterinaria")
LOGIN_DRA_FERNANDA = "fernanda.calixto"

app = Flask(__name__)


def garantir_banco_inicializado():
    # Somente desenvolvimento auto-inicializa. Ambientes publicados exigem migração explícita.
    if SETTINGS.environment in ('demo', 'production') and not DATABASE.is_file():
        raise RuntimeError('Banco não inicializado; execute migração explícita.')
    connection = sqlite3.connect(DATABASE)
    try:
        verify_database_environment(connection, SETTINGS.environment)
        tabela = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name IN ('usuarios', 'produtos', 'condicoes_clinicas', 'auth_sessions')"
        ).fetchall()
        colunas_produto = {item[1] for item in connection.execute("PRAGMA table_info(produtos)").fetchall()}
    finally:
        connection.close()
    if len(tabela) == 4 and "margem_lucro_percentual" in colunas_produto:
        return
    if SETTINGS.environment in ('demo', 'production'):
        raise RuntimeError('Schema incompleto; execute migração explícita.')
    from init_db import init_db

    init_db()


def get_db_connection():
    garantir_banco_inicializado()
    connection = sqlite3.connect(DATABASE, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON;")
    if has_request_context():
        g.setdefault('database_connections', []).append(connection)
    return connection


@app.teardown_request
def close_request_connections(error=None):
    # close() também reverte escritas não confirmadas em caminhos excepcionais.
    for connection in g.pop('database_connections', []):
        connection.close()


register_security(app, get_db_connection)


def login_obrigatorio(view_function):
    @wraps(view_function)
    def wrapped_view(*args, **kwargs):
        if "usuario_id" not in session or session.get("usuario_perfil") not in PERFIS_AUTORIZADOS:
            session.clear()
            flash("Faça login com um usuário autorizado para acessar o sistema.", "erro")
            return redirect(url_for("login"))
        return view_function(*args, **kwargs)

    return wrapped_view


def slugify_status(texto):
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    return texto.lower().replace(" ", "-")


def paginacao_args(default=20):
    """Normaliza paginação de URLs sem deixar parâmetros inválidos causarem erro."""
    try:
        pagina = max(1, int(request.args.get("pagina", 1)))
    except (TypeError, ValueError):
        pagina = 1
    try:
        por_pagina = min(100, max(1, int(request.args.get("por_pagina", default))))
    except (TypeError, ValueError):
        por_pagina = default
    return pagina, por_pagina


def csv_response(nome, cabecalho, linhas):
    saida = StringIO()
    escritor = csv.writer(saida, delimiter=";", lineterminator="\r\n")
    escritor.writerow(cabecalho)
    def safe_cell(value):
        if isinstance(value, str) and value.lstrip().startswith(('=', '+', '-', '@', '\t', '\r', '\n')):
            return "'" + value
        return value
    escritor.writerows([[safe_cell(value) for value in row] for row in linhas])
    conteudo = "\ufeff" + saida.getvalue()
    return Response(conteudo, mimetype="text/csv", headers={"Content-Disposition": f"attachment; filename={nome}"})


def row_json(item):
    return {chave: item[chave] for chave in item.keys()} if item else None


@app.template_global("url_pagina")
def url_pagina(pagina):
    parametros = request.args.to_dict()
    parametros["pagina"] = pagina
    return url_for(request.endpoint, **parametros)


def limpar_cpf(cpf):
    return "".join(char for char in cpf if char.isdigit())


def formatar_cpf(cpf):
    cpf_limpo = limpar_cpf(cpf)
    if len(cpf_limpo) != 11:
        return cpf
    return f"{cpf_limpo[:3]}.{cpf_limpo[3:6]}.{cpf_limpo[6:9]}-{cpf_limpo[9:]}"


def validar_cpf(cpf):
    cpf_limpo = limpar_cpf(cpf)
    if len(cpf_limpo) != 11 or cpf_limpo == cpf_limpo[0] * 11:
        return False
    for posicao in (9, 10):
        soma = sum(int(cpf_limpo[indice]) * ((posicao + 1) - indice) for indice in range(posicao))
        digito = (soma * 10) % 11
        digito = 0 if digito == 10 else digito
        if digito != int(cpf_limpo[posicao]):
            return False
    return True


def parse_datetime_iso(valor):
    return datetime.strptime(valor, "%Y-%m-%dT%H:%M")


def formatar_data_hora_br(valor):
    if not valor:
        return ""
    try:
        return datetime.fromisoformat(str(valor)).strftime("%d/%m/%Y %H:%M")
    except ValueError:
        return str(valor)


def formatar_hora_br(valor):
    if not valor:
        return ""
    try:
        return datetime.fromisoformat(str(valor)).strftime("%H:%M")
    except ValueError:
        return str(valor)


def formatar_data_br(valor):
    return datetime.strptime(valor, "%Y-%m-%d").strftime("%d/%m/%Y")


def breadcrumbs_padrao(*itens):
    return [("Página inicial", url_for("pagina_inicial")), *itens]


def proximo_mes(ano, mes):
    return (ano + 1, 1) if mes == 12 else (ano, mes + 1)


def mes_anterior(ano, mes):
    return (ano - 1, 12) if mes == 1 else (ano, mes - 1)


def usuario_por_login(identificador):
    connection = get_db_connection()
    usuario = connection.execute(
        """
        SELECT * FROM usuarios
        WHERE ativo = 1 AND (lower(login) = lower(?) OR lower(coalesce(nome, '')) = lower(?))
        LIMIT 1
        """,
        (identificador, identificador),
    ).fetchone()
    connection.close()
    return usuario


def usuario_atual():
    if "usuario_id" not in session:
        return None
    return {
        "id": session.get("usuario_id"),
        "login": session.get("usuario_login"),
        "nome": session.get("usuario_nome"),
        "perfil": session.get("usuario_perfil"),
    }


def limpar_caches_referencia():
    listar_especies.cache_clear()
    listar_racas_por_especie.cache_clear()
    listar_servicos.cache_clear()
    listar_veterinarios.cache_clear()


def serializar_row(row):
    return {chave: row[chave] for chave in row.keys()}


def registrar_historico(entidade, registro_id, acao, dados, connection=None):
    own_connection = connection is None
    if own_connection:
        connection = get_db_connection()
    connection.execute(
        """
        INSERT INTO historico_alteracoes (entidade, registro_id, acao, usuario_nome, dados_json, criado_em)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            entidade,
            registro_id,
            acao,
            session.get("usuario_nome") or session.get("usuario_login", "Sistema"),
            json.dumps(dados, ensure_ascii=False),
            datetime.now().strftime("%Y-%m-%dT%H:%M"),
        ),
    )
    if own_connection:
        connection.commit()
        connection.close()


@lru_cache(maxsize=1)
def listar_especies():
    connection = get_db_connection()
    especies = connection.execute("SELECT * FROM especies ORDER BY nome ASC").fetchall()
    connection.close()
    return especies


@lru_cache(maxsize=32)
def listar_racas_por_especie(especie_id):
    connection = get_db_connection()
    racas = connection.execute(
        "SELECT * FROM racas WHERE especie_id = ? ORDER BY nome ASC",
        (especie_id,),
    ).fetchall()
    connection.close()
    return racas


@lru_cache(maxsize=1)
def listar_servicos():
    connection = get_db_connection()
    servicos = connection.execute("SELECT * FROM servicos ORDER BY nome ASC").fetchall()
    connection.close()
    return servicos


@lru_cache(maxsize=1)
def listar_veterinarios():
    connection = get_db_connection()
    veterinarios = connection.execute("SELECT * FROM veterinarios ORDER BY nome ASC").fetchall()
    connection.close()
    return veterinarios


def buscar_tutores(termo_busca=""):
    connection = get_db_connection()
    if termo_busca:
        filtro = f"%{termo_busca}%"
        dados = connection.execute(
            """
            SELECT * FROM tutores
            WHERE nome LIKE ? OR telefone LIKE ? OR cpf LIKE ? OR endereco LIKE ?
            ORDER BY nome ASC
            """,
            (filtro, filtro, filtro, filtro),
        ).fetchall()
    else:
        dados = connection.execute("SELECT * FROM tutores ORDER BY nome ASC").fetchall()
    connection.close()
    return dados


def buscar_pets(termo_busca=""):
    connection = get_db_connection()
    sql = """
        SELECT pets.*, tutores.nome AS tutor_nome, especies.nome AS especie_nome, racas.nome AS raca_nome
        FROM pets
        INNER JOIN tutores ON tutores.id = pets.tutor_id
        LEFT JOIN especies ON especies.id = pets.especie_id
        LEFT JOIN racas ON racas.id = pets.raca_id
    """
    if termo_busca:
        filtro = f"%{termo_busca}%"
        sql += """
            WHERE pets.nome LIKE ? OR especies.nome LIKE ? OR racas.nome LIKE ? OR tutores.nome LIKE ?
        """
        dados = connection.execute(sql + " ORDER BY pets.nome ASC", (filtro, filtro, filtro, filtro)).fetchall()
    else:
        dados = connection.execute(sql + " ORDER BY pets.nome ASC").fetchall()
    connection.close()
    return dados


def buscar_servico(servico_id):
    connection = get_db_connection()
    servico = connection.execute("SELECT * FROM servicos WHERE id = ?", (servico_id,)).fetchone()
    connection.close()
    return servico


def calcular_duracao_total(servico_id, tipo_atendimento):
    servico = buscar_servico(servico_id)
    if not servico:
        return 0, None
    duracao = int(servico["duracao_minutos"])
    if tipo_atendimento == "Domiciliar":
        duracao += 40
    return duracao, servico


def sugestoes_alternativas(connection, veterinario_id, inicio_dt, duracao, consulta_id=None):
    sugestoes = []
    cursor = inicio_dt.replace(hour=HORARIO_INICIO, minute=0)
    fim_limite = inicio_dt.replace(hour=HORARIO_FIM, minute=0)
    while cursor <= fim_limite and len(sugestoes) < 3:
        disponivel, _ = verificar_disponibilidade(connection, veterinario_id, cursor, duracao, consulta_id, gerar_sugestoes=False)
        if disponivel and cursor >= inicio_dt:
            sugestoes.append(cursor.strftime("%H:%M"))
        cursor += timedelta(minutes=SLOT_MINUTOS)
    return sugestoes


def verificar_disponibilidade(connection, veterinario_id, inicio_dt, duracao, consulta_id=None, gerar_sugestoes=True):
    fim_dt = inicio_dt + timedelta(minutes=duracao)
    if inicio_dt.hour < HORARIO_INICIO or fim_dt > inicio_dt.replace(hour=HORARIO_FIM, minute=0):
        return False, ["08:00", "08:20", "08:40"]

    parametros = [veterinario_id, fim_dt.strftime("%Y-%m-%dT%H:%M"), inicio_dt.strftime("%Y-%m-%dT%H:%M")]
    sql = """
        SELECT id FROM consultas
        WHERE veterinario_id = ?
          AND data_hora < ?
          AND data_fim > ?
    """
    if consulta_id:
        sql += " AND id != ?"
        parametros.append(consulta_id)

    conflito = connection.execute(sql, parametros).fetchone()
    if conflito:
        return False, sugestoes_alternativas(connection, veterinario_id, inicio_dt, duracao, consulta_id) if gerar_sugestoes else []

    return True, []


def construir_grade_dia(data_iso, consultas, hora_destacada=""):
    inicio = datetime.strptime(f"{data_iso} {HORARIO_INICIO:02d}:00", "%Y-%m-%d %H:%M")
    fim = datetime.strptime(f"{data_iso} {HORARIO_FIM:02d}:00", "%Y-%m-%d %H:%M")
    grade = []
    cursor = inicio
    while cursor <= fim:
        horario = cursor.strftime("%H:%M")
        ocupadas = []
        for consulta in consultas:
            inicio_consulta = parse_datetime_iso(consulta["data_hora"])
            fim_consulta = parse_datetime_iso(consulta["data_fim"])
            if inicio_consulta <= cursor < fim_consulta:
                ocupadas.append(consulta)
        grade.append({"horario": horario, "ocupadas": ocupadas, "ativo": horario == hora_destacada})
        cursor += timedelta(minutes=SLOT_MINUTOS)
    return grade


def consultas_do_mes(ano, mes):
    connection = get_db_connection()
    prefixo = f"{ano:04d}-{mes:02d}"
    dados = connection.execute(
        """
        SELECT consultas.*, pets.nome AS pet_nome, tutores.nome AS tutor_nome,
               veterinarios.nome AS veterinario_nome, servicos.nome AS servico_nome
        FROM consultas
        INNER JOIN pets ON pets.id = consultas.pet_id
        INNER JOIN tutores ON tutores.id = pets.tutor_id
        INNER JOIN veterinarios ON veterinarios.id = consultas.veterinario_id
        INNER JOIN servicos ON servicos.id = consultas.servico_id
        WHERE substr(consultas.data_hora, 1, 7) = ?
        ORDER BY consultas.data_hora ASC
        """,
        (prefixo,),
    ).fetchall()
    connection.close()
    return dados


def consultas_do_dia(data_iso):
    connection = get_db_connection()
    dados = connection.execute(
        """
        SELECT consultas.*, pets.nome AS pet_nome, tutores.nome AS tutor_nome,
               veterinarios.nome AS veterinario_nome, servicos.nome AS servico_nome
        FROM consultas
        INNER JOIN pets ON pets.id = consultas.pet_id
        INNER JOIN tutores ON tutores.id = pets.tutor_id
        INNER JOIN veterinarios ON veterinarios.id = consultas.veterinario_id
        INNER JOIN servicos ON servicos.id = consultas.servico_id
        WHERE date(consultas.data_hora) = ?
        ORDER BY consultas.data_hora ASC
        """,
        (data_iso,),
    ).fetchall()
    connection.close()
    return dados


def calendario_mensal(ano, mes):
    totais = {}
    for consulta in consultas_do_mes(ano, mes):
        chave = consulta["data_hora"][:10]
        totais[chave] = totais.get(chave, 0) + 1
    calendario = Calendar(firstweekday=0)
    semanas = []
    for semana in calendario.monthdatescalendar(ano, mes):
        dias = []
        for dia in semana:
            chave = dia.isoformat()
            dias.append({
                "numero": dia.day,
                "data_iso": chave,
                "esta_no_mes": dia.month == mes,
                "sem_expediente": dia.weekday() >= 5,
                "total_consultas": totais.get(chave, 0),
                "tem_consultas": totais.get(chave, 0) > 0,
            })
        semanas.append(dias)
    return semanas


@app.context_processor
def inject_now():
    return {
        "agora": datetime.now(),
        "logo_url": url_for("static", filename="logo-clinica.jpg"),
        "usuario_logado": usuario_atual(),
    }


@app.template_filter("status_slug")
def status_slug_filter(valor):
    return slugify_status(valor)


@app.template_filter("data_hora_br")
def data_hora_br_filter(valor):
    return formatar_data_hora_br(valor)


@app.template_filter("hora_br")
def hora_br_filter(valor):
    return formatar_hora_br(valor)


@app.template_filter("data_br")
def data_br_filter(valor):
    return formatar_data_br(valor)


@app.route("/", methods=["GET", "POST"])
@app.route("/login", methods=["GET", "POST"])
def login():
    if "usuario_id" in session:
        return redirect(url_for("pagina_inicial"))
    if request.method == "POST":
        identificador = request.form.get("login", "").strip()
        senha = request.form.get("senha", "")
        usuario = usuario_por_login(identificador) if identificador else None
        if not identificador or not senha:
            flash("Informe o usuário e a senha para entrar.", "erro")
        elif usuario and (not app.config['PRODUCTION'] or len(senha) >= 12) and check_password_hash(usuario["senha_hash"], senha):
            connection = get_db_connection()
            try:
                start_session(connection, usuario)
            finally:
                connection.close()
            flash("Acesso liberado com sucesso.", "sucesso")
            return redirect(url_for("pagina_inicial"))
        else:
            flash("Usuário ou senha inválidos.", "erro")
    return render_template("login.html")


@app.route("/pagina-inicial")
@login_obrigatorio
def pagina_inicial():
    hoje = datetime.now().strftime("%Y-%m-%d")
    consultas_hoje = consultas_do_dia(hoje)
    connection = get_db_connection()
    totais = {
        "tutores": connection.execute("SELECT COUNT(*) FROM tutores").fetchone()[0],
        "pets": connection.execute("SELECT COUNT(*) FROM pets").fetchone()[0],
        "consultas": connection.execute("SELECT COUNT(*) FROM consultas").fetchone()[0],
    }
    estoque = resumo_estoque(connection)
    produtos_criticos = listar_produtos(connection, {"situacao": "baixo", "somente_ativos": True})[:5]
    lotes_vencendo = listar_lotes(connection, {"proximos": True})[:5]
    movimentacoes_recentes = listar_movimentacoes(connection, limite=5)
    connection.close()
    resumo = {status: 0 for status in STATUSS_CONSULTA}
    for consulta in consultas_hoje:
        resumo[consulta["status"]] += 1
    return render_template(
        "pagina_inicial.html",
        consultas_hoje=consultas_hoje,
        proximas_consultas=consultas_do_mes(datetime.now().year, datetime.now().month)[:5],
        estoque=estoque,
        produtos_criticos=produtos_criticos,
        lotes_vencendo=lotes_vencendo,
        movimentacoes_recentes=movimentacoes_recentes,
        resumo_hoje=resumo,
        totais=totais,
        secao="pagina_inicial",
        breadcrumbs=[("Página inicial", None)],
    )


@app.route("/estoque")
@login_obrigatorio
def estoque_dashboard():
    connection = get_db_connection()
    dados = resumo_estoque(connection)
    produtos_criticos = listar_produtos(connection, {"situacao": "baixo", "somente_ativos": True})[:10]
    lotes_vencendo = listar_lotes(connection, {"proximos": True})[:10]
    movimentacoes_recentes = listar_movimentacoes(connection, limite=10)
    relatorio = relatorio_consumo(connection, 30)
    consumo_30d = sum(float(item["consumo"] or 0) for item in relatorio)
    reposicao_recomendada = []
    for item in relatorio:
        produto = buscar_produto(connection, item["id"])
        consumo = consumo_por_produto(connection, item["id"], 30)
        if produto and sugestao_reposicao(produto, consumo)["disponivel"]:
            reposicao_recomendada.append(item)
    connection.close()
    return render_template(
        "estoque/dashboard.html",
        estoque=dados,
        produtos_criticos=produtos_criticos,
        lotes_vencendo=lotes_vencendo,
        movimentacoes_recentes=movimentacoes_recentes,
        consumo_30d=consumo_30d,
        reposicao_recomendada=reposicao_recomendada,
        secao="estoque",
        breadcrumbs=breadcrumbs_padrao(("Estoque", None)),
    )


@app.route("/estoque/produtos")
@login_obrigatorio
def listar_produtos_page():
    pagina, por_pagina = paginacao_args()
    filtros = {
        "busca": request.args.get("busca", "").strip(),
        "tipo": request.args.get("tipo", "").strip(),
        "categoria_id": request.args.get("categoria_id", type=int),
        "situacao": request.args.get("situacao", "").strip(),
        "somente_ativos": request.args.get("inativos") != "1",
        "paginado": True,
        "pagina": pagina,
        "por_pagina": por_pagina,
    }
    connection = get_db_connection()
    pagina_resultado = listar_produtos(connection, filtros)
    categorias = listar_categorias(connection)
    connection.close()
    return render_template(
        "estoque/produtos/lista.html",
        produtos=pagina_resultado["itens"],
        pagina_resultado=pagina_resultado,
        categorias=categorias,
        filtros=filtros,
        tipos_produto=("Medicamento", "Vacina", "Material", "Produto"),
        secao="estoque",
        estoque_subsecao="produtos",
        breadcrumbs=breadcrumbs_padrao(("Estoque", url_for("estoque_dashboard")), ("Produtos", None)),
    )


def _dados_form_produto(connection, produto=None):
    return {
        "produto": produto,
        "categorias": listar_categorias(connection, somente_ativas=True),
        "tipos_produto": ("Medicamento", "Vacina", "Material", "Produto"),
        "unidades": ("unidade", "caixa", "frasco", "ampola", "kg", "litro"),
    }


@app.route("/estoque/produtos/novo", methods=["GET", "POST"])
@login_obrigatorio
def criar_produto():
    connection = get_db_connection()
    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        codigo = request.form.get("codigo", "").strip() or None
        tipo = request.form.get("tipo", "").strip()
        categoria_id = request.form.get("categoria_id", type=int) or None
        unidade = request.form.get("unidade_medida", "unidade").strip() or "unidade"
        estoque_minimo = request.form.get("estoque_minimo", "0").strip().replace(",", ".")
        margem_lucro = request.form.get("margem_lucro_percentual", "30").strip().replace(",", ".")
        produto_form = {"nome": nome, "codigo": codigo or "", "tipo": tipo, "categoria_id": categoria_id, "unidade_medida": unidade, "estoque_minimo": estoque_minimo, "margem_lucro_percentual": margem_lucro}
        try:
            estoque_minimo = float(estoque_minimo)
            margem_lucro = float(margem_lucro)
            if not nome or tipo not in ("Medicamento", "Vacina", "Material", "Produto") or estoque_minimo < 0 or margem_lucro < 0:
                raise ValueError
            connection.execute(
                "INSERT INTO produtos (nome, codigo, tipo, categoria_id, unidade_medida, estoque_minimo, margem_lucro_percentual) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (nome, codigo, tipo, categoria_id, unidade, estoque_minimo, margem_lucro),
            )
            connection.commit()
        except (ValueError, sqlite3.IntegrityError):
            connection.close()
            flash("Preencha corretamente os dados do produto. O código deve ser único.", "erro")
            form_connection = get_db_connection()
            dados = _dados_form_produto(form_connection, produto_form)
            form_connection.close()
            return render_template("estoque/produtos/form.html", acao="Novo produto", secao="estoque", breadcrumbs=breadcrumbs_padrao(("Estoque", url_for("estoque_dashboard")), ("Produtos", url_for("listar_produtos_page")), ("Novo produto", None)), **dados)
        produto_id = connection.execute("SELECT last_insert_rowid()").fetchone()[0]
        connection.close()
        flash("Produto cadastrado com sucesso.", "sucesso")
        return redirect(url_for("detalhar_produto", produto_id=produto_id))
    dados = _dados_form_produto(connection)
    connection.close()
    return render_template("estoque/produtos/form.html", acao="Novo produto", secao="estoque", breadcrumbs=breadcrumbs_padrao(("Estoque", url_for("estoque_dashboard")), ("Produtos", url_for("listar_produtos_page")), ("Novo produto", None)), **dados)


@app.route("/estoque/produtos/<int:produto_id>/editar", methods=["GET", "POST"])
@login_obrigatorio
def editar_produto(produto_id):
    connection = get_db_connection()
    produto = buscar_produto(connection, produto_id)
    if not produto:
        connection.close()
        flash("Produto não encontrado.", "erro")
        return redirect(url_for("listar_produtos_page"))
    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        codigo = request.form.get("codigo", "").strip() or None
        tipo = request.form.get("tipo", "").strip()
        categoria_id = request.form.get("categoria_id", type=int) or None
        unidade = request.form.get("unidade_medida", "unidade").strip() or "unidade"
        estoque_minimo = request.form.get("estoque_minimo", "0").strip().replace(",", ".")
        margem_lucro = request.form.get("margem_lucro_percentual", str(produto["margem_lucro_percentual"] or 30)).strip().replace(",", ".")
        produto_form = {"id": produto_id, "nome": nome, "codigo": codigo or "", "tipo": tipo, "categoria_id": categoria_id, "unidade_medida": unidade, "estoque_minimo": estoque_minimo, "margem_lucro_percentual": margem_lucro}
        try:
            estoque_minimo = float(estoque_minimo)
            margem_lucro = float(margem_lucro)
            if not nome or tipo not in ("Medicamento", "Vacina", "Material", "Produto") or estoque_minimo < 0 or margem_lucro < 0:
                raise ValueError
            connection.execute(
                "UPDATE produtos SET nome = ?, codigo = ?, tipo = ?, categoria_id = ?, unidade_medida = ?, estoque_minimo = ?, margem_lucro_percentual = ? WHERE id = ?",
                (nome, codigo, tipo, categoria_id, unidade, estoque_minimo, margem_lucro, produto_id),
            )
            connection.commit()
        except (ValueError, sqlite3.IntegrityError):
            connection.close()
            flash("Preencha corretamente os dados do produto. O código deve ser único.", "erro")
            form_connection = get_db_connection()
            dados = _dados_form_produto(form_connection, produto_form)
            form_connection.close()
            return render_template("estoque/produtos/form.html", acao="Editar produto", secao="estoque", breadcrumbs=breadcrumbs_padrao(("Estoque", url_for("estoque_dashboard")), ("Produtos", url_for("listar_produtos_page")), ("Editar produto", None)), **dados)
        connection.close()
        flash("Produto atualizado com sucesso.", "sucesso")
        return redirect(url_for("detalhar_produto", produto_id=produto_id))
    dados = _dados_form_produto(connection, produto)
    connection.close()
    return render_template("estoque/produtos/form.html", acao="Editar produto", secao="estoque", breadcrumbs=breadcrumbs_padrao(("Estoque", url_for("estoque_dashboard")), ("Produtos", url_for("listar_produtos_page")), ("Editar produto", None)), **dados)


@app.route("/estoque/produtos/<int:produto_id>")
@login_obrigatorio
def detalhar_produto(produto_id):
    connection = get_db_connection()
    produto = buscar_produto(connection, produto_id)
    if not produto:
        connection.close()
        flash("Produto não encontrado.", "erro")
        return redirect(url_for("listar_produtos_page"))
    lotes = listar_lotes(connection, {"produto_id": produto_id})
    movimentacoes = listar_movimentacoes(connection, {"produto_id": produto_id}, limite=20)
    consumo = consumo_por_produto(connection, produto_id)
    consumo_diario = historico_consumo_diario(connection, produto_id)
    reposicao = sugestao_reposicao(produto, consumo)
    connection.close()
    dias_estimados = (float(produto["estoque_total"]) / consumo["medio_diario"]) if consumo["medio_diario"] else None
    return render_template(
        "estoque/produtos/detalhe.html",
        produto=produto,
        lotes=lotes,
        movimentacoes=movimentacoes,
        consumo=consumo,
        consumo_diario=consumo_diario,
        dias_estimados=dias_estimados,
        reposicao=reposicao,
        secao="estoque",
        breadcrumbs=breadcrumbs_padrao(("Estoque", url_for("estoque_dashboard")), ("Produtos", url_for("listar_produtos_page")), (produto["nome"], None)),
    )


@app.route("/estoque/produtos/<int:produto_id>/alternar", methods=["POST"])
@login_obrigatorio
def alternar_produto(produto_id):
    connection = get_db_connection()
    connection.execute("UPDATE produtos SET ativo = CASE ativo WHEN 1 THEN 0 ELSE 1 END WHERE id = ?", (produto_id,))
    connection.commit()
    connection.close()
    flash("Status do produto atualizado.", "sucesso")
    return redirect(url_for("listar_produtos_page"))


@app.route("/estoque/categorias", methods=["GET", "POST"])
@login_obrigatorio
def listar_categorias_page():
    connection = get_db_connection()
    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        descricao = request.form.get("descricao", "").strip()
        try:
            if not nome:
                raise ValueError
            connection.execute("INSERT INTO categorias (nome, descricao) VALUES (?, ?)", (nome, descricao))
            connection.commit()
            flash("Categoria cadastrada com sucesso.", "sucesso")
        except (ValueError, sqlite3.IntegrityError):
            connection.rollback()
            flash("Informe um nome de categoria único.", "erro")
        connection.close()
        return redirect(url_for("listar_categorias_page"))
    categorias = listar_categorias(connection, busca=request.args.get("busca", "").strip())
    connection.close()
    return render_template("estoque/categorias/lista.html", categorias=categorias, secao="estoque", estoque_subsecao="categorias", breadcrumbs=breadcrumbs_padrao(("Estoque", url_for("estoque_dashboard")), ("Categorias", None)))


@app.route("/estoque/categorias/<int:categoria_id>/editar", methods=["GET", "POST"])
@login_obrigatorio
def editar_categoria(categoria_id):
    connection = get_db_connection()
    categoria = connection.execute("SELECT * FROM categorias WHERE id = ?", (categoria_id,)).fetchone()
    if not categoria:
        connection.close()
        flash("Categoria não encontrada.", "erro")
        return redirect(url_for("listar_categorias_page"))
    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        descricao = request.form.get("descricao", "").strip()
        try:
            if not nome:
                raise ValueError
            connection.execute("UPDATE categorias SET nome = ?, descricao = ? WHERE id = ?", (nome, descricao, categoria_id))
            connection.commit()
        except (ValueError, sqlite3.IntegrityError):
            connection.close()
            flash("Informe um nome de categoria único.", "erro")
            return render_template("estoque/categorias/form.html", categoria={"id": categoria_id, "nome": nome, "descricao": descricao}, acao="Editar categoria", secao="estoque", breadcrumbs=breadcrumbs_padrao(("Estoque", url_for("estoque_dashboard")), ("Categorias", url_for("listar_categorias_page")), ("Editar categoria", None)))
        connection.close()
        flash("Categoria atualizada com sucesso.", "sucesso")
        return redirect(url_for("listar_categorias_page"))
    connection.close()
    return render_template("estoque/categorias/form.html", categoria=categoria, acao="Editar categoria", secao="estoque", breadcrumbs=breadcrumbs_padrao(("Estoque", url_for("estoque_dashboard")), ("Categorias", url_for("listar_categorias_page")), ("Editar categoria", None)))


@app.route("/estoque/categorias/<int:categoria_id>/alternar", methods=["POST"])
@login_obrigatorio
def alternar_categoria(categoria_id):
    connection = get_db_connection()
    connection.execute("UPDATE categorias SET ativo = CASE ativo WHEN 1 THEN 0 ELSE 1 END WHERE id = ?", (categoria_id,))
    connection.commit()
    connection.close()
    flash("Status da categoria atualizado.", "sucesso")
    return redirect(url_for("listar_categorias_page"))


@app.route("/estoque/fornecedores", methods=["GET", "POST"])
@login_obrigatorio
def listar_fornecedores_page():
    connection = get_db_connection()
    if request.method == "POST":
        dados = tuple(request.form.get(campo, "").strip() for campo in ("nome", "documento", "telefone", "email", "endereco"))
        try:
            if not dados[0]:
                raise ValueError
            connection.execute("INSERT INTO fornecedores (nome, documento, telefone, email, endereco) VALUES (?, ?, ?, ?, ?)", dados)
            connection.commit()
            flash("Fornecedor cadastrado com sucesso.", "sucesso")
        except (ValueError, sqlite3.IntegrityError):
            connection.rollback()
            flash("Informe um nome de fornecedor único.", "erro")
        connection.close()
        return redirect(url_for("listar_fornecedores_page"))
    pagina, por_pagina = paginacao_args()
    busca = request.args.get("busca", "").strip()
    status = request.args.get("status", "").strip()
    pagina_resultado = listar_fornecedores(connection, busca=busca, status=status, filtros={"paginado": True, "pagina": pagina, "por_pagina": por_pagina})
    connection.close()
    return render_template("estoque/fornecedores/lista.html", fornecedores=pagina_resultado["itens"], pagina_resultado=pagina_resultado, secao="estoque", estoque_subsecao="fornecedores", breadcrumbs=breadcrumbs_padrao(("Estoque", url_for("estoque_dashboard")), ("Fornecedores", None)))


@app.route("/estoque/fornecedores/<int:fornecedor_id>/editar", methods=["GET", "POST"])
@login_obrigatorio
def editar_fornecedor(fornecedor_id):
    connection = get_db_connection()
    fornecedor = connection.execute("SELECT * FROM fornecedores WHERE id = ?", (fornecedor_id,)).fetchone()
    if not fornecedor:
        connection.close()
        flash("Fornecedor não encontrado.", "erro")
        return redirect(url_for("listar_fornecedores_page"))
    if request.method == "POST":
        dados = tuple(request.form.get(campo, "").strip() for campo in ("nome", "documento", "telefone", "email", "endereco"))
        try:
            if not dados[0]:
                raise ValueError
            connection.execute("UPDATE fornecedores SET nome = ?, documento = ?, telefone = ?, email = ?, endereco = ? WHERE id = ?", (*dados, fornecedor_id))
            connection.commit()
        except (ValueError, sqlite3.IntegrityError):
            connection.close()
            flash("Informe um nome de fornecedor único.", "erro")
            return render_template("estoque/fornecedores/form.html", fornecedor=dict(zip(("nome", "documento", "telefone", "email", "endereco"), dados)), acao="Editar fornecedor", secao="estoque", breadcrumbs=breadcrumbs_padrao(("Estoque", url_for("estoque_dashboard")), ("Fornecedores", url_for("listar_fornecedores_page")), ("Editar fornecedor", None)))
        connection.close()
        flash("Fornecedor atualizado com sucesso.", "sucesso")
        return redirect(url_for("listar_fornecedores_page"))
    connection.close()
    return render_template("estoque/fornecedores/form.html", fornecedor=fornecedor, acao="Editar fornecedor", secao="estoque", breadcrumbs=breadcrumbs_padrao(("Estoque", url_for("estoque_dashboard")), ("Fornecedores", url_for("listar_fornecedores_page")), ("Editar fornecedor", None)))


@app.route("/estoque/fornecedores/<int:fornecedor_id>/alternar", methods=["POST"])
@login_obrigatorio
def alternar_fornecedor(fornecedor_id):
    connection = get_db_connection()
    connection.execute("UPDATE fornecedores SET ativo = CASE ativo WHEN 1 THEN 0 ELSE 1 END WHERE id = ?", (fornecedor_id,))
    connection.commit()
    connection.close()
    flash("Status do fornecedor atualizado.", "sucesso")
    return redirect(url_for("listar_fornecedores_page"))


@app.route("/estoque/lotes/entrada", methods=["GET", "POST"])
@login_obrigatorio
def registrar_entrada_estoque():
    connection = get_db_connection()
    produtos = listar_produtos(connection, {"somente_ativos": True})
    fornecedores = listar_fornecedores(connection, somente_ativos=True)
    if request.method == "POST":
        try:
            lote_id, _ = registrar_entrada(
                connection,
                request.form.get("produto_id", type=int),
                request.form.get("fornecedor_id", type=int),
                request.form.get("numero_lote", ""),
                request.form.get("quantidade", ""),
                request.form.get("validade", ""),
                request.form.get("valor_compra_unitario", ""),
                session.get("usuario_id"),
                request.form.get("motivo", "Compra"),
            )
        except (EstoqueError, sqlite3.IntegrityError) as erro:
            connection.close()
            flash(str(erro) or "Não foi possível registrar a entrada.", "erro")
            return render_template("estoque/lotes/entrada.html", produtos=produtos, fornecedores=fornecedores, dados=request.form, secao="estoque", breadcrumbs=breadcrumbs_padrao(("Estoque", url_for("estoque_dashboard")), ("Entrada de lote", None)))
        connection.close()
        flash("Entrada registrada e lote criado com sucesso.", "sucesso")
        return redirect(url_for("listar_lotes_page"))
    connection.close()
    return render_template("estoque/lotes/entrada.html", produtos=produtos, fornecedores=fornecedores, dados={}, secao="estoque", breadcrumbs=breadcrumbs_padrao(("Estoque", url_for("estoque_dashboard")), ("Entrada de lote", None)))


@app.route("/estoque/saidas", methods=["GET", "POST"])
@login_obrigatorio
def registrar_saida_estoque():
    connection = get_db_connection()
    produtos = listar_produtos(connection, {"somente_ativos": True})
    if request.method == "POST":
        try:
            alocacoes = registrar_saida_fefo(
                connection,
                request.form.get("produto_id", type=int),
                request.form.get("quantidade", ""),
                session.get("usuario_id"),
                request.form.get("motivo", "Saída manual"),
                valor_unitario_praticado=request.form.get("valor_unitario_praticado", ""),
            )
        except (EstoqueError, EstoqueInsuficiente, sqlite3.IntegrityError) as erro:
            connection.close()
            flash(str(erro) or "Não foi possível registrar a saída.", "erro")
            return render_template("estoque/saidas/form.html", produtos=produtos, dados=request.form, secao="estoque", breadcrumbs=breadcrumbs_padrao(("Estoque", url_for("estoque_dashboard")), ("Saída manual", None)))
        connection.close()
        lotes = ", ".join(f"{item['numero_lote']} ({item['quantidade']:g})" for item in alocacoes)
        flash(f"Saída registrada por FEFO. Lotes utilizados: {lotes}.", "sucesso")
        return redirect(url_for("listar_movimentacoes_page"))
    connection.close()
    return render_template("estoque/saidas/form.html", produtos=produtos, dados={}, secao="estoque", breadcrumbs=breadcrumbs_padrao(("Estoque", url_for("estoque_dashboard")), ("Saída manual", None)))


@app.route("/estoque/lotes")
@login_obrigatorio
def listar_lotes_page():
    connection = get_db_connection()
    pagina, por_pagina = paginacao_args()
    filtros = {"produto_id": request.args.get("produto_id", type=int), "fornecedor_id": request.args.get("fornecedor_id", type=int), "proximos": request.args.get("proximos") == "1", "vencidos": request.args.get("vencidos") == "1", "paginado": True, "pagina": pagina, "por_pagina": por_pagina}
    pagina_resultado = listar_lotes(connection, filtros)
    produtos = listar_produtos(connection, {"somente_ativos": True})
    fornecedores = listar_fornecedores(connection, somente_ativos=True)
    connection.close()
    return render_template("estoque/lotes/lista.html", lotes=pagina_resultado["itens"], pagina_resultado=pagina_resultado, produtos=produtos, fornecedores=fornecedores, filtros=filtros, secao="estoque", estoque_subsecao="lotes", breadcrumbs=breadcrumbs_padrao(("Estoque", url_for("estoque_dashboard")), ("Lotes", None)))


@app.route("/estoque/lotes/<int:lote_id>/ajuste", methods=["GET", "POST"])
@login_obrigatorio
def ajustar_lote(lote_id):
    connection = get_db_connection()
    lote = connection.execute(
        "SELECT lotes.*, produtos.nome AS produto_nome, produtos.unidade_medida FROM lotes INNER JOIN produtos ON produtos.id = lotes.produto_id WHERE lotes.id = ?",
        (lote_id,),
    ).fetchone()
    if not lote:
        connection.close()
        flash("Lote não encontrado.", "erro")
        return redirect(url_for("listar_lotes_page"))
    if request.method == "POST":
        try:
            registrar_ajuste(connection, lote_id, request.form.get("nova_quantidade", ""), session.get("usuario_id"), request.form.get("motivo", ""))
            flash("Ajuste registrado com sucesso.", "sucesso")
        except (EstoqueError, sqlite3.IntegrityError) as erro:
            flash(str(erro) or "Não foi possível registrar o ajuste.", "erro")
        finally:
            connection.close()
        return redirect(url_for("listar_lotes_page", produto_id=lote["produto_id"]))
    connection.close()
    return render_template("estoque/lotes/ajuste.html", lote=lote, dados={}, secao="estoque", breadcrumbs=breadcrumbs_padrao(("Estoque", url_for("estoque_dashboard")), ("Lotes", url_for("listar_lotes_page")), ("Ajuste", None)))


@app.route("/estoque/movimentacoes")
@login_obrigatorio
def listar_movimentacoes_page():
    pagina, por_pagina = paginacao_args()
    connection = get_db_connection()
    filtros = {"produto_id": request.args.get("produto_id", type=int), "tipo": request.args.get("tipo", "").strip(), "usuario_id": request.args.get("usuario_id", type=int), "consulta_id": request.args.get("consulta_id", type=int), "data_inicio": request.args.get("data_inicio", "").strip(), "data_fim": request.args.get("data_fim", "").strip(), "paginado": True, "pagina": pagina, "por_pagina": por_pagina}
    pagina_resultado = listar_movimentacoes(connection, filtros)
    produtos = listar_produtos(connection, {"somente_ativos": True})
    usuarios = connection.execute("SELECT id, nome FROM usuarios ORDER BY nome").fetchall()
    consultas = connection.execute("SELECT consultas.id, consultas.data_hora, pets.nome AS pet_nome FROM consultas LEFT JOIN pets ON pets.id = consultas.pet_id ORDER BY consultas.data_hora DESC LIMIT 100").fetchall()
    connection.close()
    return render_template("estoque/movimentacoes/lista.html", movimentacoes=pagina_resultado["itens"], pagina_resultado=pagina_resultado, produtos=produtos, usuarios=usuarios, consultas=consultas, filtros=filtros, tipos_movimentacao=("Entrada", "Saída", "Ajuste", "Estorno"), secao="estoque", estoque_subsecao="movimentacoes", breadcrumbs=breadcrumbs_padrao(("Estoque", url_for("estoque_dashboard")), ("Movimentações", None)))


@app.route("/estoque/relatorios")
@login_obrigatorio
def relatorios_estoque():
    dias = request.args.get("dias", type=int) or 30
    dias = min(max(dias, 7), 365)
    produto_id = request.args.get("produto_id", type=int)
    categoria_id = request.args.get("categoria_id", type=int)
    connection = get_db_connection()
    relatorio = relatorio_consumo(connection, dias, produto_id, categoria_id)
    categorias = listar_categorias(connection)
    produtos_filtro = listar_produtos(connection, {"somente_ativos": True})
    # Indicadores de apresentação derivados das mesmas movimentações já usadas no relatório.
    hoje = datetime.now().date()
    inicio = (hoje - timedelta(days=dias - 1)).isoformat()
    consumo_diario = connection.execute(
        """
        SELECT date(criado_em) AS dia, COALESCE(SUM(quantidade), 0) AS quantidade
        FROM movimentacoes_estoque
        WHERE tipo = 'Saída' AND date(criado_em) >= date(?)
        GROUP BY date(criado_em)
        ORDER BY dia ASC
        """,
        (inicio,),
    ).fetchall()
    consumo_por_dia = {item["dia"]: float(item["quantidade"]) for item in consumo_diario}
    dias_consumo = []
    for indice in range(dias):
        dia = (hoje - timedelta(days=dias - 1 - indice)).isoformat()
        dias_consumo.append({"dia": dia, "quantidade": consumo_por_dia.get(dia, 0)})
    produtos_reposicao = []
    for item in relatorio:
        produto = buscar_produto(connection, item["id"])
        consumo = consumo_por_produto(connection, item["id"], dias)
        if produto and sugestao_reposicao(produto, consumo)["disponivel"]:
            produtos_reposicao.append(item)
    connection.close()
    return render_template(
        "estoque/relatorios.html",
        relatorio=relatorio,
        dias=dias,
        consumo_diario=dias_consumo,
        produtos_reposicao=produtos_reposicao,
        categorias=categorias,
        produtos_filtro=produtos_filtro,
        filtros={"produto_id": produto_id, "categoria_id": categoria_id},
        secao="estoque",
        estoque_subsecao="relatorios",
        breadcrumbs=breadcrumbs_padrao(("Estoque", url_for("estoque_dashboard")), ("Relatórios", None)),
    )


@app.route("/estoque/exportar/movimentacoes.csv")
@login_obrigatorio
def exportar_movimentacoes_csv():
    connection = get_db_connection()
    filtros = {"produto_id": request.args.get("produto_id", type=int), "tipo": request.args.get("tipo", "").strip(), "usuario_id": request.args.get("usuario_id", type=int), "consulta_id": request.args.get("consulta_id", type=int), "data_inicio": request.args.get("data_inicio", "").strip(), "data_fim": request.args.get("data_fim", "").strip()}
    dados = listar_movimentacoes(connection, filtros)
    connection.close()
    return csv_response("movimentacoes.csv", ["Data", "Produto", "Lote", "Tipo", "Quantidade", "Valor sugerido", "Valor praticado", "Motivo", "Consulta", "Usuário"], [[item["criado_em"], item["produto_nome"], item["numero_lote"], item["tipo"], item["quantidade"], item["valor_unitario_sugerido"], item["valor_unitario_praticado"], item["motivo"], item["pet_nome"] or "", item["usuario_nome"] or ""] for item in dados])


@app.route("/api/estoque/resumo")
@login_obrigatorio
def api_estoque_resumo():
    connection = get_db_connection()
    resumo = resumo_estoque(connection)
    connection.close()
    return jsonify(resumo)


@app.route("/api/estoque/produtos")
@login_obrigatorio
def api_estoque_produtos():
    pagina, por_pagina = paginacao_args()
    filtros = {"busca": request.args.get("busca", "").strip(), "tipo": request.args.get("tipo", "").strip(), "categoria_id": request.args.get("categoria_id", type=int), "situacao": request.args.get("situacao", "").strip(), "somente_ativos": request.args.get("inativos") != "1", "paginado": True, "pagina": pagina, "por_pagina": por_pagina}
    connection = get_db_connection()
    resultado = listar_produtos(connection, filtros)
    connection.close()
    return jsonify({"data": [row_json(item) for item in resultado["itens"]], "meta": {chave: resultado[chave] for chave in ("pagina", "por_pagina", "total", "total_paginas")}})


@app.route("/api/estoque/movimentacoes")
@login_obrigatorio
def api_estoque_movimentacoes():
    pagina, por_pagina = paginacao_args()
    filtros = {"produto_id": request.args.get("produto_id", type=int), "tipo": request.args.get("tipo", "").strip(), "usuario_id": request.args.get("usuario_id", type=int), "consulta_id": request.args.get("consulta_id", type=int), "data_inicio": request.args.get("data_inicio", "").strip(), "data_fim": request.args.get("data_fim", "").strip(), "paginado": True, "pagina": pagina, "por_pagina": por_pagina}
    connection = get_db_connection()
    resultado = listar_movimentacoes(connection, filtros)
    connection.close()
    return jsonify({"data": [row_json(item) for item in resultado["itens"]], "meta": {chave: resultado[chave] for chave in ("pagina", "por_pagina", "total", "total_paginas")}})


@app.route("/estoque/exportar/posicao.csv")
@login_obrigatorio
def exportar_posicao_csv():
    connection = get_db_connection()
    filtros = {"busca": request.args.get("busca", "").strip(), "tipo": request.args.get("tipo", "").strip(), "categoria_id": request.args.get("categoria_id", type=int), "situacao": request.args.get("situacao", "").strip(), "somente_ativos": True}
    dados = listar_produtos(connection, filtros)
    connection.close()
    return csv_response("posicao-estoque.csv", ["Produto", "Código", "Tipo", "Categoria", "Estoque", "Mínimo", "Valor estimado"], [[item["nome"], item["codigo"] or "", item["tipo"], item["categoria_nome"] or "", item["estoque_total"], item["estoque_minimo"], round(float(item["valor_estoque"] or 0), 2)] for item in dados])


@app.route("/estoque/exportar/consumo.csv")
@login_obrigatorio
def exportar_consumo_csv():
    dias = request.args.get("dias", type=int) or 30
    dias = min(max(dias, 7), 365)
    connection = get_db_connection()
    dados = relatorio_consumo(connection, dias, request.args.get("produto_id", type=int), request.args.get("categoria_id", type=int))
    connection.close()
    return csv_response("consumo-estoque.csv", ["Produto", "Tipo", "Categoria", "Consumo", "Estoque atual", "Valor do estoque"], [[item["nome"], item["tipo"], item["categoria_nome"] or "", item["consumo"], item["estoque_atual"], item["valor_estoque"]] for item in dados])


@app.route("/estoque/movimentacoes/<int:movimentacao_id>/estornar", methods=["POST"])
@login_obrigatorio
def estornar_movimentacao(movimentacao_id):
    connection = get_db_connection()
    try:
        registrar_estorno(connection, movimentacao_id, session.get("usuario_id"))
        flash("Movimentação estornada com sucesso.", "sucesso")
    except EstoqueError as erro:
        flash(str(erro), "erro")
    finally:
        connection.close()
    return redirect(url_for("listar_movimentacoes_page"))


@app.route("/api/racas")
@login_obrigatorio
def api_racas():
    especie_id = request.args.get("especie_id", type=int)
    if not especie_id:
        return jsonify({"racas": []})
    racas = [{"id": r["id"], "nome": r["nome"]} for r in listar_racas_por_especie(especie_id)]
    return jsonify({"racas": racas})


@app.route("/api/disponibilidade")
@login_obrigatorio
def api_disponibilidade():
    data_hora = request.args.get("data_hora", "").strip()
    servico_id = request.args.get("servico_id", type=int)
    tipo_atendimento = request.args.get("tipo_atendimento", "").strip()
    veterinario_id = request.args.get("veterinario_id", type=int)
    consulta_id = request.args.get("consulta_id", type=int)
    if not data_hora or not servico_id or not tipo_atendimento or not veterinario_id:
        return jsonify({"disponivel": False, "mensagem": "Preencha data, serviço, tipo de atendimento e veterinário."}), 400
    duracao, _ = calcular_duracao_total(servico_id, tipo_atendimento)
    if not duracao:
        return jsonify({"disponivel": False, "mensagem": "O serviço informado não foi encontrado."}), 400
    try:
        inicio_dt = parse_datetime_iso(data_hora)
    except ValueError:
        return jsonify({"disponivel": False, "mensagem": "Informe uma data e hora válidas no formato solicitado."}), 400
    connection = get_db_connection()
    disponivel, sugestoes = verificar_disponibilidade(connection, veterinario_id, inicio_dt, duracao, consulta_id)
    connection.close()
    mensagem = "Horário disponível." if disponivel else "Conflito com outro agendamento para este veterinário."
    if sugestoes and not disponivel:
        mensagem += f" Sugestoes: {', '.join(sugestoes)}."
    return jsonify({"disponivel": disponivel, "mensagem": mensagem, "duracao_total_minutos": duracao, "sugestoes": sugestoes})


@app.route("/tutores")
@login_obrigatorio
def listar_tutores():
    busca = request.args.get("busca", "").strip()
    return render_template("tutores/lista.html", tutores=buscar_tutores(busca), busca=busca, secao="tutores", breadcrumbs=breadcrumbs_padrao(("Tutores", None)))


@app.route("/tutores/novo", methods=["GET", "POST"])
@login_obrigatorio
def criar_tutor():
    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        telefone = request.form.get("telefone", "").strip()
        cpf = request.form.get("cpf", "").strip()
        endereco = request.form.get("endereco", "").strip()
        tutor = {"nome": nome, "telefone": telefone, "cpf": cpf, "endereco": endereco}
        if not nome or not telefone or not cpf:
            flash("Nome, telefone e CPF do tutor são obrigatórios.", "erro")
            return render_template("tutores/form.html", tutor=tutor, acao="Novo Tutor", secao="tutores", breadcrumbs=breadcrumbs_padrao(("Tutores", url_for("listar_tutores")), ("Novo tutor", None)))
        if not validar_cpf(cpf):
            flash("Informe um CPF válido no formato XXX.XXX.XXX-XX.", "erro")
            return render_template("tutores/form.html", tutor=tutor, acao="Novo Tutor", secao="tutores", breadcrumbs=breadcrumbs_padrao(("Tutores", url_for("listar_tutores")), ("Novo tutor", None)))
        connection = get_db_connection()
        try:
            inserted = connection.execute("INSERT INTO tutores (nome, telefone, cpf, endereco) VALUES (?, ?, ?, ?)", (nome, telefone, formatar_cpf(cpf), endereco))
            novo = connection.execute("SELECT * FROM tutores WHERE id = ?", (inserted.lastrowid,)).fetchone()
            registrar_historico("tutores", novo["id"], "criado", serializar_row(novo), connection)
            connection.commit()
        except sqlite3.IntegrityError:
            connection.close()
            flash("Já existe um tutor cadastrado com este CPF.", "erro")
            return render_template("tutores/form.html", tutor=tutor, acao="Novo Tutor", secao="tutores", breadcrumbs=breadcrumbs_padrao(("Tutores", url_for("listar_tutores")), ("Novo tutor", None)))
        connection.close()
        flash("Tutor cadastrado com sucesso.", "sucesso")
        return redirect(url_for("listar_tutores"))
    return render_template("tutores/form.html", tutor=None, acao="Novo Tutor", secao="tutores", breadcrumbs=breadcrumbs_padrao(("Tutores", url_for("listar_tutores")), ("Novo tutor", None)))


@app.route("/tutores/<int:tutor_id>/editar", methods=["GET", "POST"])
@login_obrigatorio
def editar_tutor(tutor_id):
    connection = get_db_connection()
    tutor = connection.execute("SELECT * FROM tutores WHERE id = ?", (tutor_id,)).fetchone()
    connection.close()
    if not tutor:
        flash("Tutor não encontrado.", "erro")
        return redirect(url_for("listar_tutores"))
    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        telefone = request.form.get("telefone", "").strip()
        cpf = request.form.get("cpf", "").strip()
        endereco = request.form.get("endereco", "").strip()
        dados = {"id": tutor_id, "nome": nome, "telefone": telefone, "cpf": cpf, "endereco": endereco}
        if not nome or not telefone or not cpf or not validar_cpf(cpf):
            flash("Preencha corretamente o nome, o telefone e o CPF do tutor.", "erro")
            return render_template("tutores/form.html", tutor=dados, acao="Editar Tutor", secao="tutores", breadcrumbs=breadcrumbs_padrao(("Tutores", url_for("listar_tutores")), ("Editar tutor", None)))
        try:
            connection = get_db_connection()
            connection.execute('BEGIN IMMEDIATE')
            original = connection.execute("SELECT * FROM tutores WHERE id = ?", (tutor_id,)).fetchone()
            connection.execute("UPDATE tutores SET nome = ?, telefone = ?, cpf = ?, endereco = ? WHERE id = ?", (nome, telefone, formatar_cpf(cpf), endereco, tutor_id))
            registrar_historico("tutores", tutor_id, "editado", {"antes": serializar_row(original), "depois": dados}, connection)
            connection.commit()
            connection.close()
        except sqlite3.IntegrityError:
            flash("Já existe outro tutor cadastrado com este CPF.", "erro")
            return render_template("tutores/form.html", tutor=dados, acao="Editar Tutor", secao="tutores", breadcrumbs=breadcrumbs_padrao(("Tutores", url_for("listar_tutores")), ("Editar tutor", None)))
        flash("Tutor atualizado com sucesso.", "sucesso")
        return redirect(url_for("listar_tutores"))
    return render_template("tutores/form.html", tutor=tutor, acao="Editar Tutor", secao="tutores", breadcrumbs=breadcrumbs_padrao(("Tutores", url_for("listar_tutores")), ("Editar tutor", None)))


@app.route("/tutores/<int:tutor_id>/excluir", methods=["POST"])
@login_obrigatorio
def excluir_tutor(tutor_id):
    connection = get_db_connection()
    connection.execute('BEGIN IMMEDIATE')
    tutor = connection.execute("SELECT * FROM tutores WHERE id = ?", (tutor_id,)).fetchone()
    total = connection.execute("SELECT COUNT(*) FROM pets WHERE tutor_id = ?", (tutor_id,)).fetchone()[0]
    if total:
        connection.close()
        flash("Não é possível excluir um tutor que possui animais cadastrados.", "erro")
        return redirect(url_for("listar_tutores"))
    connection.execute("DELETE FROM tutores WHERE id = ?", (tutor_id,))
    if tutor:
        registrar_historico("tutores", tutor_id, "excluido", serializar_row(tutor), connection)
    connection.commit()
    connection.close()
    flash("Tutor excluido com sucesso.", "sucesso")
    return redirect(url_for("listar_tutores"))


@app.route("/pets")
@login_obrigatorio
def listar_pets():
    busca = request.args.get("busca", "").strip()
    return render_template("pets/lista.html", pets=buscar_pets(busca), busca=busca, secao="pets", breadcrumbs=breadcrumbs_padrao(("Animais", None)))


def dados_form_pet():
    return {
        "especies": listar_especies(),
        "tutores": buscar_tutores(),
    }


@app.route("/pets/novo", methods=["GET", "POST"])
@login_obrigatorio
def criar_pet():
    contexto = dados_form_pet()
    if not contexto["tutores"]:
        flash("Cadastre pelo menos um tutor antes de cadastrar animais.", "erro")
        return redirect(url_for("listar_tutores"))
    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        especie_id = request.form.get("especie_id", type=int)
        raca_id = request.form.get("raca_id", type=int)
        raca_personalizada = request.form.get("raca_personalizada", "").strip()
        idade = request.form.get("idade", "").strip()
        tutor_id = request.form.get("tutor_id", type=int)
        historico = request.form.get("historico", "").strip()
        especie = next((item for item in contexto["especies"] if item["id"] == especie_id), None)
        raca = None if not raca_id else next((item for item in listar_racas_por_especie(especie_id) if item["id"] == raca_id), None)
        nome_raca = raca_personalizada if not raca else raca["nome"]
        pet = {"nome": nome, "especie_id": especie_id, "raca_id": raca_id, "raca_personalizada": raca_personalizada, "idade": idade, "tutor_id": tutor_id, "historico": historico}
        if not nome or not especie or not tutor_id or not nome_raca:
            flash("Preencha os campos obrigatórios do animal.", "erro")
            return render_template("pets/form.html", pet=pet, acao="Novo Animal", secao="pets", breadcrumbs=breadcrumbs_padrao(("Animais", url_for("listar_pets")), ("Novo animal", None)), **contexto)
        connection = get_db_connection()
        try:
            inserted = connection.execute(
                "INSERT INTO pets (nome, especie_id, especie, raca_id, raca, idade, tutor_id, historico) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (nome, especie_id, especie["nome"], raca_id, nome_raca, idade, tutor_id, historico),
            )
            novo = connection.execute("SELECT * FROM pets WHERE id = ?", (inserted.lastrowid,)).fetchone()
            registrar_historico("pets", novo["id"], "criado", serializar_row(novo), connection)
            connection.commit()
            connection.close()
        except sqlite3.IntegrityError:
            connection.close()
            flash("Não foi possível salvar o animal. Revise a espécie e a raça selecionadas.", "erro")
            return render_template("pets/form.html", pet=pet, acao="Novo Animal", secao="pets", breadcrumbs=breadcrumbs_padrao(("Animais", url_for("listar_pets")), ("Novo animal", None)), **contexto)
        flash("Animal cadastrado com sucesso.", "sucesso")
        return redirect(url_for("listar_pets"))
    return render_template("pets/form.html", pet=None, acao="Novo Animal", secao="pets", breadcrumbs=breadcrumbs_padrao(("Animais", url_for("listar_pets")), ("Novo animal", None)), **contexto)


@app.route("/pets/<int:pet_id>/editar", methods=["GET", "POST"])
@login_obrigatorio
def editar_pet(pet_id):
    contexto = dados_form_pet()
    connection = get_db_connection()
    pet_db = connection.execute("SELECT * FROM pets WHERE id = ?", (pet_id,)).fetchone()
    connection.close()
    if not pet_db:
        flash("Animal não encontrado.", "erro")
        return redirect(url_for("listar_pets"))
    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        especie_id = request.form.get("especie_id", type=int)
        raca_id = request.form.get("raca_id", type=int)
        raca_personalizada = request.form.get("raca_personalizada", "").strip()
        idade = request.form.get("idade", "").strip()
        tutor_id = request.form.get("tutor_id", type=int)
        historico = request.form.get("historico", "").strip()
        especie = next((item for item in contexto["especies"] if item["id"] == especie_id), None)
        raca = None if not raca_id else next((item for item in listar_racas_por_especie(especie_id) if item["id"] == raca_id), None)
        nome_raca = raca_personalizada if not raca else raca["nome"]
        pet = {"id": pet_id, "nome": nome, "especie_id": especie_id, "raca_id": raca_id, "raca_personalizada": raca_personalizada, "idade": idade, "tutor_id": tutor_id, "historico": historico}
        if not nome or not especie or not tutor_id or not nome_raca:
            flash("Preencha os campos obrigatórios do animal.", "erro")
            return render_template("pets/form.html", pet=pet, acao="Editar Animal", secao="pets", breadcrumbs=breadcrumbs_padrao(("Animais", url_for("listar_pets")), ("Editar animal", None)), **contexto)
        try:
            connection = get_db_connection()
            connection.execute('BEGIN IMMEDIATE')
            original = connection.execute("SELECT * FROM pets WHERE id = ?", (pet_id,)).fetchone()
            connection.execute(
                "UPDATE pets SET nome = ?, especie_id = ?, especie = ?, raca_id = ?, raca = ?, idade = ?, tutor_id = ?, historico = ? WHERE id = ?",
                (nome, especie_id, especie["nome"], raca_id, nome_raca, idade, tutor_id, historico, pet_id),
            )
            registrar_historico("pets", pet_id, "editado", {"antes": serializar_row(original), "depois": pet}, connection)
            connection.commit()
            connection.close()
        except sqlite3.IntegrityError:
            flash("Não foi possível atualizar o animal. Revise a espécie e a raça selecionadas.", "erro")
            return render_template("pets/form.html", pet=pet, acao="Editar Animal", secao="pets", breadcrumbs=breadcrumbs_padrao(("Animais", url_for("listar_pets")), ("Editar animal", None)), **contexto)
        flash("Animal atualizado com sucesso.", "sucesso")
        return redirect(url_for("listar_pets"))
    return render_template("pets/form.html", pet=pet_db, acao="Editar Animal", secao="pets", breadcrumbs=breadcrumbs_padrao(("Animais", url_for("listar_pets")), ("Editar animal", None)), **contexto)


@app.route("/pets/<int:pet_id>/excluir", methods=["POST"])
@login_obrigatorio
def excluir_pet(pet_id):
    connection = get_db_connection()
    connection.execute('BEGIN IMMEDIATE')
    pet = connection.execute("SELECT * FROM pets WHERE id = ?", (pet_id,)).fetchone()
    total = connection.execute("SELECT COUNT(*) FROM consultas WHERE pet_id = ?", (pet_id,)).fetchone()[0]
    conditions = connection.execute('SELECT 1 FROM condicoes_clinicas WHERE pet_id=?', (pet_id,)).fetchone()
    if total or conditions or (pet and pet['historico']):
        connection.close()
        flash("Não é possível excluir um animal com consultas, condições ou histórico clínico.", "erro")
        return redirect(url_for("listar_pets"))
    connection.execute("DELETE FROM pets WHERE id = ?", (pet_id,))
    if pet:
        registrar_historico("pets", pet_id, "excluido", serializar_row(pet), connection)
    connection.commit()
    connection.close()
    flash("Animal excluido com sucesso.", "sucesso")
    return redirect(url_for("listar_pets"))


def contexto_form_consulta():
    return {
        "pets": buscar_pets(),
        "servicos": listar_servicos(),
        "veterinarios": listar_veterinarios(),
        "status_confirmacao": STATUSS_CONFIRMACAO,
        "tipos_atendimento": TIPOS_ATENDIMENTO,
    }


def obter_historico(entidade, registro_id):
    connection = get_db_connection()
    historico = connection.execute(
        """
        SELECT * FROM historico_alteracoes
        WHERE entidade = ? AND registro_id = ?
        ORDER BY criado_em DESC, id DESC
        """,
        (entidade, registro_id),
    ).fetchall()
    connection.close()
    return historico


def buscar_consulta_detalhada(consulta_id):
    connection = get_db_connection()
    consulta = connection.execute(
        """
        SELECT consultas.*, pets.nome AS pet_nome, pets.historico AS pet_historico,
               tutores.nome AS tutor_nome, veterinarios.nome AS veterinario_nome,
               servicos.nome AS servico_nome
        FROM consultas
        INNER JOIN pets ON pets.id = consultas.pet_id
        INNER JOIN tutores ON tutores.id = pets.tutor_id
        INNER JOIN veterinarios ON veterinarios.id = consultas.veterinario_id
        INNER JOIN servicos ON servicos.id = consultas.servico_id
        WHERE consultas.id = ?
        """,
        (consulta_id,),
    ).fetchone()
    connection.close()
    return consulta


def historico_clinico_pet(pet_id):
    connection = get_db_connection()
    registros = connection.execute(
        """
        SELECT consultas.*, pets.nome AS pet_nome, pets.historico AS pet_historico,
               tutores.nome AS tutor_nome, veterinarios.nome AS veterinario_nome,
               servicos.nome AS servico_nome
        FROM consultas
        INNER JOIN pets ON pets.id = consultas.pet_id
        INNER JOIN tutores ON tutores.id = pets.tutor_id
        INNER JOIN veterinarios ON veterinarios.id = consultas.veterinario_id
        INNER JOIN servicos ON servicos.id = consultas.servico_id
        WHERE consultas.pet_id = ?
        ORDER BY consultas.data_hora DESC, consultas.id DESC
        """,
        (pet_id,),
    ).fetchall()
    connection.close()
    return registros


def buscar_pet_detalhado(pet_id):
    connection = get_db_connection()
    pet = connection.execute(
        """
        SELECT pets.*, tutores.nome AS tutor_nome, tutores.telefone AS tutor_telefone
        FROM pets
        INNER JOIN tutores ON tutores.id = pets.tutor_id
        WHERE pets.id = ?
        """,
        (pet_id,),
    ).fetchone()
    connection.close()
    return pet


def condicoes_clinicas_pet(pet_id):
    connection = get_db_connection()
    condicoes = connection.execute(
        """
        SELECT * FROM condicoes_clinicas
        WHERE pet_id = ?
        ORDER BY CASE status WHEN 'Ativa' THEN 0 WHEN 'Controlada' THEN 1 ELSE 2 END,
                 registrado_em DESC, id DESC
        """,
        (pet_id,),
    ).fetchall()
    connection.close()
    return condicoes


def salvar_consulta(formulario, consulta_id=None):
    data_hora = formulario.get("data_hora", "").strip()
    pet_id = formulario.get("pet_id", type=int)
    servico_id = formulario.get("servico_id", type=int)
    veterinario_id = formulario.get("veterinario_id", type=int)
    tipo_atendimento = formulario.get("tipo_atendimento", "").strip()
    confirmacao_status = formulario.get("confirmacao_status", "").strip()
    observacoes = formulario.get("observacoes", "").strip()
    diagnostico = formulario.get("diagnostico", "").strip()
    tratamento = formulario.get("tratamento", "").strip()
    vacinas = formulario.get("vacinas", "").strip()
    status = formulario.get("status", "Agendada").strip()
    consulta = {
        "id": consulta_id,
        "data_hora": data_hora,
        "pet_id": pet_id,
        "servico_id": servico_id,
        "veterinario_id": veterinario_id,
        "tipo_atendimento": tipo_atendimento,
        "confirmacao_status": confirmacao_status,
        "observacoes": observacoes,
        "diagnostico": diagnostico,
        "tratamento": tratamento,
        "vacinas": vacinas,
        "status": status,
    }
    if not data_hora or not pet_id or not servico_id or not veterinario_id or tipo_atendimento not in TIPOS_ATENDIMENTO or confirmacao_status not in STATUSS_CONFIRMACAO or status not in STATUSS_CONSULTA:
        return False, "Preencha corretamente os campos obrigatórios da consulta.", consulta, []
    duracao, servico = calcular_duracao_total(servico_id, tipo_atendimento)
    if not servico:
        return False, "Serviço inexistente.", consulta, []
    try:
        inicio_dt = parse_datetime_iso(data_hora)
        if not 1900 <= inicio_dt.year <= 2100:
            raise ValueError('Data fora do intervalo permitido.')
    except ValueError:
        return False, "Informe uma data e hora válidas para a consulta.", consulta, []
    fim_dt = inicio_dt + timedelta(minutes=duracao)
    connection = get_db_connection()
    if not connection.execute('SELECT 1 FROM pets WHERE id=?', (pet_id,)).fetchone() or not connection.execute('SELECT 1 FROM veterinarios WHERE id=?', (veterinario_id,)).fetchone():
        connection.close()
        return False, "Paciente ou veterinário inexistente.", consulta, []
    connection.execute('BEGIN IMMEDIATE')
    disponivel, sugestoes = verificar_disponibilidade(connection, veterinario_id, inicio_dt, duracao, consulta_id)
    if not disponivel:
        connection.close()
        mensagem = "Conflito de horario para este veterinario."
        if sugestoes:
            mensagem += f" Horários alternativos: {', '.join(sugestoes)}."
        return False, mensagem, consulta, sugestoes
    try:
        if consulta_id:
            connection.execute(
                """
                UPDATE consultas
                SET data_hora = ?, data_fim = ?, pet_id = ?, servico_id = ?, tipo_consulta = ?,
                    duracao_total_minutos = ?, veterinario_id = ?, tipo_atendimento = ?,
                    observacoes = ?, diagnostico = ?, tratamento = ?, vacinas = ?,
                    status = ?, confirmacao_status = ?
                WHERE id = ?
                """,
                (
                    data_hora,
                    fim_dt.strftime("%Y-%m-%dT%H:%M"),
                    pet_id,
                    servico_id,
                    servico["nome"],
                    duracao,
                    veterinario_id,
                    tipo_atendimento,
                    observacoes,
                    diagnostico,
                    tratamento,
                    vacinas,
                    status,
                    confirmacao_status,
                    consulta_id,
                ),
            )
        else:
            connection.execute(
                """
                INSERT INTO consultas (data_hora, data_fim, pet_id, servico_id, tipo_consulta, duracao_total_minutos, veterinario_id, tipo_atendimento, observacoes, diagnostico, tratamento, vacinas, status, confirmacao_status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    data_hora,
                    fim_dt.strftime("%Y-%m-%dT%H:%M"),
                    pet_id,
                    servico_id,
                    servico["nome"],
                    duracao,
                    veterinario_id,
                    tipo_atendimento,
                    observacoes,
                    diagnostico,
                    tratamento,
                    vacinas,
                    status,
                    confirmacao_status,
                ),
            )
        record_id = consulta_id or connection.execute('SELECT last_insert_rowid()').fetchone()[0]
        registro = connection.execute('SELECT * FROM consultas WHERE id=?', (record_id,)).fetchone()
        registrar_historico('consultas', record_id, 'editado' if consulta_id else 'criado', serializar_row(registro), connection)
        connection.commit()
    except sqlite3.IntegrityError:
        connection.rollback()
        connection.close()
        return False, "Não foi possível gravar: verifique vínculos e conflito de horário.", consulta, []
    except Exception:
        connection.rollback()
        connection.close()
        raise
    connection.close()
    return True, "", consulta, []


@app.route("/consultas")
@login_obrigatorio
def listar_consultas():
    hoje = datetime.now()
    ano = request.args.get("ano", type=int) or hoje.year
    mes = request.args.get("mes", type=int) or hoje.month
    if not 1900 <= ano <= 2100 or not 1 <= mes <= 12:
        flash("O período informado não é válido. Exibindo o mês atual.", "erro")
        ano, mes = hoje.year, hoje.month
    ano_anterior, mes_anterior_valor = mes_anterior(ano, mes)
    ano_proximo, mes_proximo_valor = proximo_mes(ano, mes)
    return render_template(
        "consultas/lista.html",
        calendario=calendario_mensal(ano, mes),
        consultas_mes=consultas_do_mes(ano, mes)[:10],
        ano=ano,
        mes=mes,
        nome_mes=MESES_PT[mes],
        ano_anterior=ano_anterior,
        mes_anterior=mes_anterior_valor,
        ano_proximo=ano_proximo,
        mes_proximo=mes_proximo_valor,
        secao="consultas",
        breadcrumbs=breadcrumbs_padrao(("Consultas", None)),
    )


@app.route("/consultas/nova", methods=["GET", "POST"])
@login_obrigatorio
def criar_consulta():
    contexto = contexto_form_consulta()
    if request.method == "POST":
        sucesso, mensagem, consulta, _ = salvar_consulta(request.form)
        if not sucesso:
            flash(mensagem, "erro")
            return render_template("consultas/form.html", consulta=consulta, acao="Nova Consulta", secao="consultas", breadcrumbs=breadcrumbs_padrao(("Consultas", url_for("listar_consultas")), ("Nova consulta", None)), **contexto)
        flash("Consulta cadastrada com sucesso.", "sucesso")
        return redirect(url_for("listar_consultas"))
    pet_id = request.args.get("pet_id", type=int)
    consulta_inicial = {"pet_id": pet_id} if pet_id else None
    return render_template("consultas/form.html", consulta=consulta_inicial, acao="Nova Consulta", secao="consultas", breadcrumbs=breadcrumbs_padrao(("Consultas", url_for("listar_consultas")), ("Nova consulta", None)), **contexto)


@app.route("/consultas/<int:consulta_id>/editar", methods=["GET", "POST"])
@login_obrigatorio
def editar_consulta(consulta_id):
    contexto = contexto_form_consulta()
    connection = get_db_connection()
    consulta = connection.execute("SELECT * FROM consultas WHERE id = ?", (consulta_id,)).fetchone()
    connection.close()
    if not consulta:
        flash("Consulta não encontrada.", "erro")
        return redirect(url_for("listar_consultas"))
    if request.method == "POST":
        sucesso, mensagem, consulta_form, _ = salvar_consulta(request.form, consulta_id)
        if not sucesso:
            flash(mensagem, "erro")
            return render_template("consultas/form.html", consulta=consulta_form, acao="Editar Consulta", secao="consultas", breadcrumbs=breadcrumbs_padrao(("Consultas", url_for("listar_consultas")), ("Editar consulta", None)), **contexto)
        flash("Consulta atualizada com sucesso.", "sucesso")
        return redirect(url_for("listar_consultas"))
    return render_template("consultas/form.html", consulta=consulta, acao="Editar Consulta", secao="consultas", breadcrumbs=breadcrumbs_padrao(("Consultas", url_for("listar_consultas")), ("Editar consulta", None)), **contexto)


@app.route("/consultas/<int:consulta_id>/produtos", methods=["POST"])
@login_obrigatorio
def adicionar_produto_consulta(consulta_id):
    produto_id = request.form.get("produto_id", type=int)
    quantidade = request.form.get("quantidade", "")
    motivo = request.form.get("motivo", "Uso em atendimento").strip()
    connection = get_db_connection()
    try:
        registrar_uso_consulta(
            connection,
            consulta_id,
            produto_id,
            quantidade,
            session.get("usuario_id"),
            motivo,
            request.form.get("valor_unitario_praticado", ""),
        )
        flash("Produto utilizado registrado e estoque atualizado por FEFO.", "sucesso")
    except (EstoqueError, EstoqueInsuficiente, sqlite3.IntegrityError) as erro:
        flash(str(erro) or "Não foi possível registrar o produto utilizado.", "erro")
    finally:
        connection.close()
    return redirect(url_for("visualizar_historico", entidade="consultas", registro_id=consulta_id))


@app.route("/consultas/<int:consulta_id>/excluir", methods=["POST"])
@login_obrigatorio
def excluir_consulta(consulta_id):
    connection = get_db_connection()
    try:
        connection.execute('BEGIN IMMEDIATE')
        consulta = connection.execute("SELECT * FROM consultas WHERE id = ?", (consulta_id,)).fetchone()
        if consulta and consulta['status'] == 'Concluida':
            connection.rollback()
            flash('Atendimento concluído deve ser preservado. Registre correções no histórico clínico.', 'erro')
            return redirect(url_for('listar_consultas'))
        if consulta and consulta['status'] != 'Cancelada':
            connection.execute("UPDATE consultas SET status='Cancelada' WHERE id = ?", (consulta_id,))
            registrar_historico("consultas", consulta_id, "cancelado", serializar_row(consulta), connection)
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
    flash("Consulta cancelada; histórico e produtos utilizados preservados. Cancelamento não estorna estoque.", "sucesso")
    return redirect(url_for("listar_consultas"))


@app.route("/consultas/dia/<data_iso>")
@login_obrigatorio
def agenda_do_dia(data_iso):
    hora = request.args.get("hora", "").strip()
    try:
        datetime.strptime(data_iso, "%Y-%m-%d")
    except ValueError:
        flash("A data informada não é válida.", "erro")
        return redirect(url_for("listar_consultas"))
    consultas = consultas_do_dia(data_iso)
    detalhes = []
    if hora:
        try:
            momento = datetime.strptime(f"{data_iso}T{hora}", "%Y-%m-%dT%H:%M")
        except ValueError:
            flash("O horário informado não é válido.", "erro")
            return redirect(url_for("agenda_do_dia", data_iso=data_iso))
        for consulta in consultas:
            if parse_datetime_iso(consulta["data_hora"]) <= momento < parse_datetime_iso(consulta["data_fim"]):
                detalhes.append(consulta)
    return render_template(
        "consultas/dia.html",
        consultas=consultas,
        grade=construir_grade_dia(data_iso, consultas, hora),
        data_iso=data_iso,
        hora_selecionada=hora,
        detalhes_horario=detalhes,
        secao="consultas",
        breadcrumbs=breadcrumbs_padrao(("Consultas", url_for("listar_consultas")), ("Agenda do dia", None)),
    )


@app.route("/pets/<int:pet_id>/condicoes", methods=["POST"])
@login_obrigatorio
def adicionar_condicao_clinica(pet_id):
    condicao = request.form.get("condicao", "").strip()
    observacoes = request.form.get("observacoes", "").strip()
    status = request.form.get("status", "Ativa").strip()
    connection = get_db_connection()
    pet = connection.execute("SELECT id FROM pets WHERE id = ?", (pet_id,)).fetchone()
    if not pet:
        connection.close()
        flash("Paciente não encontrado.", "erro")
        return redirect(url_for("listar_pets"))
    if not condicao or status not in STATUSS_CONDICAO:
        connection.close()
        flash("Informe a condição clínica e um status válido.", "erro")
        return redirect(url_for("historico_clinico_pet_page", pet_id=pet_id))
    registrado_em = datetime.now().strftime("%Y-%m-%dT%H:%M")
    cursor = connection.execute(
        """
        INSERT INTO condicoes_clinicas (pet_id, condicao, observacoes, status, registrado_em, usuario_nome)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (pet_id, condicao, observacoes, status, registrado_em, session.get("usuario_nome") or session.get("usuario_login", "Sistema")),
    )
    condicao_id = cursor.lastrowid
    registrar_historico("condicoes_clinicas", condicao_id, "criada", {"pet_id": pet_id, "condicao": condicao, "status": status}, connection)
    connection.commit()
    connection.close()
    flash("Condição clínica adicionada ao prontuário.", "sucesso")
    return redirect(url_for("historico_clinico_pet_page", pet_id=pet_id))


@app.route("/pets/<int:pet_id>/historico-clinico")
@login_obrigatorio
def historico_clinico_pet_page(pet_id):
    pet = buscar_pet_detalhado(pet_id)
    if not pet:
        flash("Paciente não encontrado.", "erro")
        return redirect(url_for("listar_pets"))
    return render_template(
        "consultas/historico.html",
        pet=pet,
        consulta=None,
        historico_clinico=historico_clinico_pet(pet_id),
        condicoes=condicoes_clinicas_pet(pet_id),
        auditoria=[],
        itens_consulta=[],
        produtos_estoque=[],
        status_condicao=STATUSS_CONDICAO,
        secao="pets",
        breadcrumbs=breadcrumbs_padrao(("Animais", url_for("listar_pets")), ("Prontuário clínico", None)),
    )


@app.route("/historico/<entidade>/<int:registro_id>")
@login_obrigatorio
def visualizar_historico(entidade, registro_id):
    if entidade == "consultas":
        consulta = buscar_consulta_detalhada(registro_id)
        if not consulta:
            flash("Consulta não encontrada.", "erro")
            return redirect(url_for("listar_consultas"))
        connection = get_db_connection()
        itens = listar_itens_consulta(connection, registro_id)
        produtos_estoque = listar_produtos(connection, {"somente_ativos": True})
        connection.close()
        return render_template(
            "consultas/historico.html",
            pet=buscar_pet_detalhado(consulta["pet_id"]),
            consulta=consulta,
            historico_clinico=historico_clinico_pet(consulta["pet_id"]),
            condicoes=condicoes_clinicas_pet(consulta["pet_id"]),
            auditoria=obter_historico(entidade, registro_id),
            itens_consulta=itens,
            produtos_estoque=produtos_estoque,
            status_condicao=STATUSS_CONDICAO,
            secao="consultas",
            breadcrumbs=breadcrumbs_padrao(("Consultas", url_for("listar_consultas")), ("Histórico clínico", None)),
        )
    titulos = {
        "tutores": "Histórico do tutor",
        "pets": "Histórico do animal",
        "consultas": "Histórico da consulta",
        "servicos": "Histórico do serviço",
        "veterinarios": "Histórico do veterinário",
    }
    return render_template(
        "historico.html",
        historico=obter_historico(entidade, registro_id),
        titulo=titulos.get(entidade, "Histórico"),
        entidade=entidade,
        registro_id=registro_id,
        secao=entidade if entidade in ("tutores", "pets", "consultas", "servicos", "veterinarios") else "configuracoes",
        breadcrumbs=breadcrumbs_padrao((titulos.get(entidade, "Histórico"), None)),
    )


@app.route("/servicos")
@login_obrigatorio
def listar_servicos_page():
    return render_template("servicos/lista.html", servicos=listar_servicos(), secao="servicos", breadcrumbs=breadcrumbs_padrao(("Serviços", None)))


@app.route("/veterinarios")
@login_obrigatorio
def listar_veterinarios_page():
    return render_template("veterinarios/lista.html", veterinarios=listar_veterinarios(), secao="veterinarios", breadcrumbs=breadcrumbs_padrao(("Veterinários", None)))


@app.route("/servicos/<int:servico_id>/editar", methods=["GET", "POST"])
@login_obrigatorio
def editar_servico(servico_id):
    connection = get_db_connection()
    servico = connection.execute("SELECT * FROM servicos WHERE id = ?", (servico_id,)).fetchone()
    connection.close()
    if not servico:
        flash("Serviço não encontrado.", "erro")
        return redirect(url_for("listar_servicos_page"))
    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        duracao = request.form.get("duracao_minutos", type=int)
        dados = {"id": servico_id, "nome": nome, "duracao_minutos": duracao}
        if not nome or not duracao or not 20 <= duracao <= 1440:
            flash("Informe um nome e duração mínima de 20 minutos.", "erro")
            return render_template("servicos/form.html", servico=dados, acao="Editar serviço", secao="servicos", breadcrumbs=breadcrumbs_padrao(("Serviços", url_for("listar_servicos_page")), ("Editar serviço", None)))
        connection = get_db_connection()
        connection.execute('BEGIN IMMEDIATE')
        original = connection.execute("SELECT * FROM servicos WHERE id = ?", (servico_id,)).fetchone()
        connection.execute("UPDATE servicos SET nome = ?, duracao_minutos = ? WHERE id = ?", (nome, duracao, servico_id))
        registrar_historico("servicos", servico_id, "editado", {"antes": serializar_row(original), "depois": dados}, connection)
        connection.commit()
        connection.close()
        limpar_caches_referencia()
        flash("Serviço atualizado com sucesso.", "sucesso")
        return redirect(url_for("listar_servicos_page"))
    return render_template("servicos/form.html", servico=servico, acao="Editar serviço", secao="servicos", breadcrumbs=breadcrumbs_padrao(("Serviços", url_for("listar_servicos_page")), ("Editar serviço", None)))


@app.route("/servicos/<int:servico_id>/excluir", methods=["POST"])
@login_obrigatorio
def excluir_servico(servico_id):
    connection = get_db_connection()
    connection.execute('BEGIN IMMEDIATE')
    servico = connection.execute("SELECT * FROM servicos WHERE id = ?", (servico_id,)).fetchone()
    uso = connection.execute("SELECT COUNT(*) FROM consultas WHERE servico_id = ?", (servico_id,)).fetchone()[0]
    if uso:
        connection.close()
        flash("Não é possível excluir um serviço já utilizado em consultas.", "erro")
        return redirect(url_for("listar_servicos_page"))
    connection.execute("DELETE FROM servicos WHERE id = ?", (servico_id,))
    if servico:
        registrar_historico("servicos", servico_id, "excluido", serializar_row(servico), connection)
    connection.commit()
    connection.close()
    limpar_caches_referencia()
    flash("Serviço excluído com sucesso.", "sucesso")
    return redirect(url_for("listar_servicos_page"))


@app.route("/veterinarios/<int:veterinario_id>/editar", methods=["GET", "POST"])
@login_obrigatorio
def editar_veterinario(veterinario_id):
    connection = get_db_connection()
    veterinario = connection.execute("SELECT * FROM veterinarios WHERE id = ?", (veterinario_id,)).fetchone()
    connection.close()
    if not veterinario:
        flash("Veterinário não encontrado.", "erro")
        return redirect(url_for("listar_veterinarios_page"))
    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        dados = {"id": veterinario_id, "nome": nome}
        if not nome:
            flash("Informe o nome do veterinário.", "erro")
            return render_template("veterinarios/form.html", veterinario=dados, acao="Editar veterinário", secao="veterinarios", breadcrumbs=breadcrumbs_padrao(("Veterinários", url_for("listar_veterinarios_page")), ("Editar veterinário", None)))
        connection = get_db_connection()
        connection.execute('BEGIN IMMEDIATE')
        original = connection.execute("SELECT * FROM veterinarios WHERE id = ?", (veterinario_id,)).fetchone()
        connection.execute("UPDATE veterinarios SET nome = ? WHERE id = ?", (nome, veterinario_id))
        registrar_historico("veterinarios", veterinario_id, "editado", {"antes": serializar_row(original), "depois": dados}, connection)
        connection.commit()
        connection.close()
        limpar_caches_referencia()
        flash("Veterinário atualizado com sucesso.", "sucesso")
        return redirect(url_for("listar_veterinarios_page"))
    return render_template("veterinarios/form.html", veterinario=veterinario, acao="Editar veterinário", secao="veterinarios", breadcrumbs=breadcrumbs_padrao(("Veterinários", url_for("listar_veterinarios_page")), ("Editar veterinário", None)))


@app.route("/veterinarios/<int:veterinario_id>/excluir", methods=["POST"])
@login_obrigatorio
def excluir_veterinario(veterinario_id):
    if request.form.get("confirmar_exclusao") != "sim":
        flash("Confirme a exclusão para continuar.", "erro")
        return redirect(url_for("listar_veterinarios_page"))
    connection = get_db_connection()
    connection.execute('BEGIN IMMEDIATE')
    veterinario = connection.execute("SELECT * FROM veterinarios WHERE id = ?", (veterinario_id,)).fetchone()
    clinical = connection.execute("SELECT 1 FROM consultas c WHERE c.veterinario_id=? AND (c.status != 'Agendada' OR EXISTS (SELECT 1 FROM itens_consulta i WHERE i.consulta_id=c.id)) LIMIT 1", (veterinario_id,)).fetchone()
    if clinical:
        connection.close()
        flash('Veterinário com atendimentos clínicos deve ser preservado para manter a autoria.', 'erro')
        return redirect(url_for('listar_veterinarios_page'))
    uso = connection.execute("SELECT COUNT(*) FROM consultas WHERE veterinario_id = ?", (veterinario_id,)).fetchone()[0]
    total = connection.execute("SELECT COUNT(*) FROM veterinarios").fetchone()[0]
    if not veterinario:
        connection.close()
        flash("Veterinário não encontrado.", "erro")
        return redirect(url_for("listar_veterinarios_page"))
    if total <= 1:
        connection.close()
        flash("Não é possível excluir o último veterinário cadastrado.", "erro")
        return redirect(url_for("listar_veterinarios_page"))
    substituto = connection.execute(
        """
        SELECT * FROM veterinarios
        WHERE id != ?
        ORDER BY CASE WHEN lower(nome) = lower(?) THEN 0 ELSE 1 END, nome ASC
        LIMIT 1
        """,
        (veterinario_id, "Dra. Fernanda Calixto"),
    ).fetchone()
    if uso and not substituto:
        connection.close()
        flash("Não foi encontrado outro veterinário para receber os atendimentos vinculados.", "erro")
        return redirect(url_for("listar_veterinarios_page"))
    try:
        if uso:
            connection.execute(
                "UPDATE consultas SET veterinario_id = ? WHERE veterinario_id = ?",
                (substituto["id"], veterinario_id),
            )
        connection.execute("DELETE FROM veterinarios WHERE id = ?", (veterinario_id,))
        registrar_historico(
            "veterinarios", veterinario_id, "excluido",
            {**serializar_row(veterinario), "consultas_redistribuidas": uso,
             "novo_veterinario_id": substituto["id"] if uso and substituto else None,
             "novo_veterinario_nome": substituto["nome"] if uso and substituto else None}, connection,
        )
        connection.commit()
    except sqlite3.IntegrityError:
        connection.rollback()
        connection.close()
        flash("Não foi possível excluir o veterinário por causa de vínculos ativos no banco de dados.", "erro")
        return redirect(url_for("listar_veterinarios_page"))
    connection.close()
    limpar_caches_referencia()
    if uso and substituto:
        flash(
            f"Veterinário excluído com sucesso. {uso} consulta(s) foram transferidas para {substituto['nome']}.",
            "sucesso",
        )
    else:
        flash("Veterinário excluído com sucesso.", "sucesso")
    return redirect(url_for("listar_veterinarios_page"))


@app.route("/logout", methods=["POST"])
def logout():
    connection = get_db_connection()
    try:
        end_session(connection)
    finally:
        connection.close()
    flash("Sessão encerrada com sucesso.", "sucesso")
    return redirect(url_for("login"))


@app.route('/conta/senha', methods=['GET', 'POST'])
@login_obrigatorio
def alterar_senha():
    if request.method == 'POST':
        if not check_password_hash(g.current_user['senha_hash'], request.form.get('senha_atual', '')):
            flash('Não foi possível alterar a senha. Confira os dados.', 'erro')
        elif request.form.get('nova_senha') != request.form.get('confirmacao'):
            flash('A confirmação da senha não confere.', 'erro')
        elif check_password_hash(g.current_user['senha_hash'], request.form.get('nova_senha', '')):
            flash('A nova senha deve ser diferente da senha atual.', 'erro')
        else:
            try:
                hashed = password_hash(request.form.get('nova_senha', ''))
            except ValueError as error:
                flash(str(error), 'erro')
            else:
                connection = get_db_connection()
                try:
                    changed = connection.execute('UPDATE usuarios SET senha_hash=?,session_version=session_version+1,must_change_password=0 WHERE id=? AND ativo=1 AND session_version=?', (hashed, g.current_user['id'], g.current_user['session_version']))
                    if changed.rowcount != 1:
                        connection.rollback()
                        session.clear()
                        return redirect(url_for('login'))
                    connection.execute('DELETE FROM auth_sessions WHERE usuario_id=?', (g.current_user['id'],))
                    connection.execute("INSERT INTO security_events(usuario_id,evento) VALUES (?,'password_changed')", (g.current_user['id'],))
                    connection.commit()
                    if g.current_user['must_change_password']:
                        user = connection.execute('SELECT * FROM usuarios WHERE id=?', (g.current_user['id'],)).fetchone()
                        start_session(connection, user)
                        flash('Nova senha definida com sucesso.', 'sucesso')
                        return redirect(url_for('pagina_inicial'))
                finally:
                    connection.close()
                session.clear()
                return redirect(url_for('login'))
    return render_template('conta_senha.html', primeiro_acesso=bool(g.current_user['must_change_password']), secao='conta', breadcrumbs=[('Minha conta', None)])


@app.route('/health')
def health():
    return jsonify(status='ok', version=os.environ.get('RENDER_GIT_COMMIT', 'local'))


@app.errorhandler(404)
def pagina_nao_encontrada(error):
    if "usuario_id" not in session:
        return redirect(url_for("login"))
    flash("A página solicitada não foi encontrada.", "erro")
    return redirect(url_for("pagina_inicial"))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=False)
