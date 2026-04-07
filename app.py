from calendar import Calendar
from datetime import datetime, timedelta
from functools import lru_cache
from functools import wraps
import os
from pathlib import Path
import json
import sqlite3
import unicodedata

from flask import Flask, flash, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash


BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "banco.db"
STATUSS_CONSULTA = ("Agendada", "Concluida", "Cancelada")
STATUSS_CONFIRMACAO = ("Pendente", "Confirmada", "Nao confirmada")
TIPOS_ATENDIMENTO = ("Presencial", "Domiciliar")
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
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "univet-chave-inicial-dev")


def get_db_connection():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON;")
    return connection


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
    return parse_datetime_iso(valor).strftime("%d/%m/%Y %H:%M") if valor else ""


def formatar_hora_br(valor):
    return parse_datetime_iso(valor).strftime("%H:%M") if valor else ""


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


def registrar_historico(entidade, registro_id, acao, dados):
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
        senha = request.form.get("senha", "").strip()
        usuario = usuario_por_login(identificador) if identificador else None
        if not identificador or not senha:
            flash("Informe o usuário e a senha para entrar.", "erro")
        elif usuario and check_password_hash(usuario["senha_hash"], senha):
            session["usuario_id"] = usuario["id"]
            session["usuario_login"] = usuario["login"]
            session["usuario_nome"] = usuario["nome"] or usuario["login"]
            session["usuario_perfil"] = usuario["perfil"]
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
    connection.close()
    resumo = {status: 0 for status in STATUSS_CONSULTA}
    for consulta in consultas_hoje:
        resumo[consulta["status"]] += 1
    return render_template(
        "pagina_inicial.html",
        consultas_hoje=consultas_hoje,
        proximas_consultas=consultas_do_mes(datetime.now().year, datetime.now().month)[:5],
        resumo_hoje=resumo,
        totais=totais,
        secao="pagina_inicial",
        breadcrumbs=[("Página inicial", None)],
    )


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
        return jsonify({"disponivel": False, "mensagem": "Preencha data, serviço, tipo de atendimento e veterinário."})
    duracao, _ = calcular_duracao_total(servico_id, tipo_atendimento)
    inicio_dt = parse_datetime_iso(data_hora)
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
            connection.execute("INSERT INTO tutores (nome, telefone, cpf, endereco) VALUES (?, ?, ?, ?)", (nome, telefone, formatar_cpf(cpf), endereco))
            connection.commit()
        except sqlite3.IntegrityError:
            connection.close()
            flash("Já existe um tutor cadastrado com este CPF.", "erro")
            return render_template("tutores/form.html", tutor=tutor, acao="Novo Tutor", secao="tutores", breadcrumbs=breadcrumbs_padrao(("Tutores", url_for("listar_tutores")), ("Novo tutor", None)))
        connection.close()
        connection = get_db_connection()
        novo = connection.execute("SELECT * FROM tutores WHERE cpf = ?", (formatar_cpf(cpf),)).fetchone()
        connection.close()
        if novo:
            registrar_historico("tutores", novo["id"], "criado", serializar_row(novo))
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
            original = connection.execute("SELECT * FROM tutores WHERE id = ?", (tutor_id,)).fetchone()
            connection.execute("UPDATE tutores SET nome = ?, telefone = ?, cpf = ?, endereco = ? WHERE id = ?", (nome, telefone, formatar_cpf(cpf), endereco, tutor_id))
            connection.commit()
            connection.close()
        except sqlite3.IntegrityError:
            flash("Já existe outro tutor cadastrado com este CPF.", "erro")
            return render_template("tutores/form.html", tutor=dados, acao="Editar Tutor", secao="tutores", breadcrumbs=breadcrumbs_padrao(("Tutores", url_for("listar_tutores")), ("Editar tutor", None)))
        registrar_historico("tutores", tutor_id, "editado", {"antes": serializar_row(original), "depois": dados})
        flash("Tutor atualizado com sucesso.", "sucesso")
        return redirect(url_for("listar_tutores"))
    return render_template("tutores/form.html", tutor=tutor, acao="Editar Tutor", secao="tutores", breadcrumbs=breadcrumbs_padrao(("Tutores", url_for("listar_tutores")), ("Editar tutor", None)))


@app.route("/tutores/<int:tutor_id>/excluir", methods=["POST"])
@login_obrigatorio
def excluir_tutor(tutor_id):
    connection = get_db_connection()
    tutor = connection.execute("SELECT * FROM tutores WHERE id = ?", (tutor_id,)).fetchone()
    total = connection.execute("SELECT COUNT(*) FROM pets WHERE tutor_id = ?", (tutor_id,)).fetchone()[0]
    if total:
        connection.close()
        flash("Não é possível excluir um tutor que possui animais cadastrados.", "erro")
        return redirect(url_for("listar_tutores"))
    connection.execute("DELETE FROM tutores WHERE id = ?", (tutor_id,))
    connection.commit()
    connection.close()
    if tutor:
        registrar_historico("tutores", tutor_id, "excluido", serializar_row(tutor))
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
        if not nome or not especie_id or not tutor_id or not nome_raca:
            flash("Preencha os campos obrigatórios do animal.", "erro")
            return render_template("pets/form.html", pet=pet, acao="Novo Animal", secao="pets", breadcrumbs=breadcrumbs_padrao(("Animais", url_for("listar_pets")), ("Novo animal", None)), **contexto)
        connection = get_db_connection()
        try:
            connection.execute(
                "INSERT INTO pets (nome, especie_id, especie, raca_id, raca, idade, tutor_id, historico) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (nome, especie_id, especie["nome"], raca_id, nome_raca, idade, tutor_id, historico),
            )
            connection.commit()
            connection.close()
        except sqlite3.IntegrityError:
            connection.close()
            flash("Não foi possível salvar o animal. Revise a espécie e a raça selecionadas.", "erro")
            return render_template("pets/form.html", pet=pet, acao="Novo Animal", secao="pets", breadcrumbs=breadcrumbs_padrao(("Animais", url_for("listar_pets")), ("Novo animal", None)), **contexto)
        connection = get_db_connection()
        novo = connection.execute("SELECT * FROM pets ORDER BY id DESC LIMIT 1").fetchone()
        connection.close()
        if novo:
            registrar_historico("pets", novo["id"], "criado", serializar_row(novo))
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
        if not nome or not especie_id or not tutor_id or not nome_raca:
            flash("Preencha os campos obrigatórios do animal.", "erro")
            return render_template("pets/form.html", pet=pet, acao="Editar Animal", secao="pets", breadcrumbs=breadcrumbs_padrao(("Animais", url_for("listar_pets")), ("Editar animal", None)), **contexto)
        try:
            connection = get_db_connection()
            original = connection.execute("SELECT * FROM pets WHERE id = ?", (pet_id,)).fetchone()
            connection.execute(
                "UPDATE pets SET nome = ?, especie_id = ?, especie = ?, raca_id = ?, raca = ?, idade = ?, tutor_id = ?, historico = ? WHERE id = ?",
                (nome, especie_id, especie["nome"], raca_id, nome_raca, idade, tutor_id, historico, pet_id),
            )
            connection.commit()
            connection.close()
        except sqlite3.IntegrityError:
            flash("Não foi possível atualizar o animal. Revise a espécie e a raça selecionadas.", "erro")
            return render_template("pets/form.html", pet=pet, acao="Editar Animal", secao="pets", breadcrumbs=breadcrumbs_padrao(("Animais", url_for("listar_pets")), ("Editar animal", None)), **contexto)
        registrar_historico("pets", pet_id, "editado", {"antes": serializar_row(original), "depois": pet})
        flash("Animal atualizado com sucesso.", "sucesso")
        return redirect(url_for("listar_pets"))
    return render_template("pets/form.html", pet=pet_db, acao="Editar Animal", secao="pets", breadcrumbs=breadcrumbs_padrao(("Animais", url_for("listar_pets")), ("Editar animal", None)), **contexto)


@app.route("/pets/<int:pet_id>/excluir", methods=["POST"])
@login_obrigatorio
def excluir_pet(pet_id):
    connection = get_db_connection()
    pet = connection.execute("SELECT * FROM pets WHERE id = ?", (pet_id,)).fetchone()
    total = connection.execute("SELECT COUNT(*) FROM consultas WHERE pet_id = ?", (pet_id,)).fetchone()[0]
    if total:
        connection.close()
        flash("Não é possível excluir um animal com consultas cadastradas.", "erro")
        return redirect(url_for("listar_pets"))
    connection.execute("DELETE FROM pets WHERE id = ?", (pet_id,))
    connection.commit()
    connection.close()
    if pet:
        registrar_historico("pets", pet_id, "excluido", serializar_row(pet))
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
    inicio_dt = parse_datetime_iso(data_hora)
    fim_dt = inicio_dt + timedelta(minutes=duracao)
    connection = get_db_connection()
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
        connection.commit()
    except sqlite3.IntegrityError:
        connection.close()
        return False, "Horário inicial já utilizado para este veterinário.", consulta, []
    if consulta_id:
        registro = connection.execute("SELECT * FROM consultas WHERE id = ?", (consulta_id,)).fetchone()
        registrar_historico("consultas", consulta_id, "editado", serializar_row(registro))
    else:
        registro = connection.execute("SELECT * FROM consultas ORDER BY id DESC LIMIT 1").fetchone()
        registrar_historico("consultas", registro["id"], "criado", serializar_row(registro))
    connection.close()
    return True, "", consulta, []


@app.route("/consultas")
@login_obrigatorio
def listar_consultas():
    hoje = datetime.now()
    ano = request.args.get("ano", type=int) or hoje.year
    mes = request.args.get("mes", type=int) or hoje.month
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
    return render_template("consultas/form.html", consulta=None, acao="Nova Consulta", secao="consultas", breadcrumbs=breadcrumbs_padrao(("Consultas", url_for("listar_consultas")), ("Nova consulta", None)), **contexto)


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


@app.route("/consultas/<int:consulta_id>/excluir", methods=["POST"])
@login_obrigatorio
def excluir_consulta(consulta_id):
    connection = get_db_connection()
    consulta = connection.execute("SELECT * FROM consultas WHERE id = ?", (consulta_id,)).fetchone()
    connection.execute("DELETE FROM consultas WHERE id = ?", (consulta_id,))
    connection.commit()
    connection.close()
    if consulta:
        registrar_historico("consultas", consulta_id, "excluido", serializar_row(consulta))
    flash("Consulta excluida com sucesso.", "sucesso")
    return redirect(url_for("listar_consultas"))


@app.route("/consultas/dia/<data_iso>")
@login_obrigatorio
def agenda_do_dia(data_iso):
    hora = request.args.get("hora", "").strip()
    consultas = consultas_do_dia(data_iso)
    detalhes = []
    if hora:
        momento = datetime.strptime(f"{data_iso}T{hora}", "%Y-%m-%dT%H:%M")
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


@app.route("/historico/<entidade>/<int:registro_id>")
@login_obrigatorio
def visualizar_historico(entidade, registro_id):
    if entidade == "consultas":
        consulta = buscar_consulta_detalhada(registro_id)
        if not consulta:
            flash("Consulta não encontrada.", "erro")
            return redirect(url_for("listar_consultas"))
        return render_template(
            "consultas/historico.html",
            consulta=consulta,
            historico_clinico=historico_clinico_pet(consulta["pet_id"]),
            auditoria=obter_historico(entidade, registro_id),
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
        secao=entidade if entidade in ("tutores", "pets", "consultas") else "configuracoes",
        breadcrumbs=breadcrumbs_padrao((titulos.get(entidade, "Histórico"), None)),
    )


@app.route("/servicos")
@login_obrigatorio
def listar_servicos_page():
    return render_template("servicos/lista.html", servicos=listar_servicos(), secao="configuracoes", breadcrumbs=breadcrumbs_padrao(("Serviços", None)))


@app.route("/veterinarios")
@login_obrigatorio
def listar_veterinarios_page():
    return render_template("veterinarios/lista.html", veterinarios=listar_veterinarios(), secao="configuracoes", breadcrumbs=breadcrumbs_padrao(("Veterinários", None)))


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
        if not nome or not duracao or duracao < 20:
            flash("Informe um nome e duração mínima de 20 minutos.", "erro")
            return render_template("servicos/form.html", servico=dados, acao="Editar serviço", secao="configuracoes", breadcrumbs=breadcrumbs_padrao(("Serviços", url_for("listar_servicos_page")), ("Editar serviço", None)))
        connection = get_db_connection()
        original = connection.execute("SELECT * FROM servicos WHERE id = ?", (servico_id,)).fetchone()
        connection.execute("UPDATE servicos SET nome = ?, duracao_minutos = ? WHERE id = ?", (nome, duracao, servico_id))
        connection.commit()
        connection.close()
        limpar_caches_referencia()
        registrar_historico("servicos", servico_id, "editado", {"antes": serializar_row(original), "depois": dados})
        flash("Serviço atualizado com sucesso.", "sucesso")
        return redirect(url_for("listar_servicos_page"))
    return render_template("servicos/form.html", servico=servico, acao="Editar serviço", secao="configuracoes", breadcrumbs=breadcrumbs_padrao(("Serviços", url_for("listar_servicos_page")), ("Editar serviço", None)))


@app.route("/servicos/<int:servico_id>/excluir", methods=["POST"])
@login_obrigatorio
def excluir_servico(servico_id):
    connection = get_db_connection()
    servico = connection.execute("SELECT * FROM servicos WHERE id = ?", (servico_id,)).fetchone()
    uso = connection.execute("SELECT COUNT(*) FROM consultas WHERE servico_id = ?", (servico_id,)).fetchone()[0]
    if uso:
        connection.close()
        flash("Não é possível excluir um serviço já utilizado em consultas.", "erro")
        return redirect(url_for("listar_servicos_page"))
    connection.execute("DELETE FROM servicos WHERE id = ?", (servico_id,))
    connection.commit()
    connection.close()
    limpar_caches_referencia()
    if servico:
        registrar_historico("servicos", servico_id, "excluido", serializar_row(servico))
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
            return render_template("veterinarios/form.html", veterinario=dados, acao="Editar veterinário", secao="configuracoes", breadcrumbs=breadcrumbs_padrao(("Veterinários", url_for("listar_veterinarios_page")), ("Editar veterinário", None)))
        connection = get_db_connection()
        original = connection.execute("SELECT * FROM veterinarios WHERE id = ?", (veterinario_id,)).fetchone()
        connection.execute("UPDATE veterinarios SET nome = ? WHERE id = ?", (nome, veterinario_id))
        connection.commit()
        connection.close()
        limpar_caches_referencia()
        registrar_historico("veterinarios", veterinario_id, "editado", {"antes": serializar_row(original), "depois": dados})
        flash("Veterinário atualizado com sucesso.", "sucesso")
        return redirect(url_for("listar_veterinarios_page"))
    return render_template("veterinarios/form.html", veterinario=veterinario, acao="Editar veterinário", secao="configuracoes", breadcrumbs=breadcrumbs_padrao(("Veterinários", url_for("listar_veterinarios_page")), ("Editar veterinário", None)))


@app.route("/veterinarios/<int:veterinario_id>/excluir", methods=["POST"])
@login_obrigatorio
def excluir_veterinario(veterinario_id):
    if request.form.get("confirmar_exclusao") != "sim":
        flash("Confirme a exclusão para continuar.", "erro")
        return redirect(url_for("listar_veterinarios_page"))
    connection = get_db_connection()
    veterinario = connection.execute("SELECT * FROM veterinarios WHERE id = ?", (veterinario_id,)).fetchone()
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
        connection.commit()
    except sqlite3.IntegrityError:
        connection.rollback()
        connection.close()
        flash("Não foi possível excluir o veterinário por causa de vínculos ativos no banco de dados.", "erro")
        return redirect(url_for("listar_veterinarios_page"))
    connection.close()
    limpar_caches_referencia()
    if veterinario:
        registrar_historico(
            "veterinarios",
            veterinario_id,
            "excluido",
            {
                **serializar_row(veterinario),
                "consultas_redistribuidas": uso,
                "novo_veterinario_id": substituto["id"] if uso and substituto else None,
                "novo_veterinario_nome": substituto["nome"] if uso and substituto else None,
            },
        )
    if uso and substituto:
        flash(
            f"Veterinário excluído com sucesso. {uso} consulta(s) foram transferidas para {substituto['nome']}.",
            "sucesso",
        )
    else:
        flash("Veterinário excluído com sucesso.", "sucesso")
    return redirect(url_for("listar_veterinarios_page"))


@app.route("/logout")
def logout():
    session.clear()
    flash("Sessão encerrada com sucesso.", "sucesso")
    return redirect(url_for("login"))


@app.errorhandler(404)
def pagina_nao_encontrada(error):
    if "usuario_id" not in session:
        return redirect(url_for("login"))
    flash("A página solicitada não foi encontrada.", "erro")
    return redirect(url_for("pagina_inicial"))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=False)
