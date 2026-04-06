from calendar import Calendar
from datetime import datetime
from functools import wraps
from pathlib import Path
import sqlite3
import unicodedata

from flask import Flask, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash


BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "banco.db"

STATUSS_CONSULTA = ("Agendada", "Concluida", "Cancelada")
STATUSS_CONFIRMACAO = ("Pendente", "Confirmada", "Nao confirmada")
TIPOS_CONSULTA = (
    "Consulta clinica",
    "Retorno",
    "Vacinação",
    "Exames",
    "Cirurgia",
    "Banho e tosa",
    "Avaliação",
    "Emergencia",
)
ESPECIES_SUGERIDAS = (
    "cao", "gato", "ave", "reptil", "roedor", "peixe", "equino",
    "bovino", "suino", "ave de rapina", "primata", "mustelideo", "lagomorfo",
)
RACAS_COMUNS = (
    "Labrador Retriever", "Golden Retriever", "Bulldog Frances", "Poodle", "Yorkshire Terrier",
    "Beagle", "Rottweiler", "Pastor Alemao", "SRD", "Persa", "Siames", "Maine Coon", "Sphynx",
    "Ragdoll", "British Shorthair", "Shih Tzu", "Spitz Alemao", "Pinscher", "Maltes",
    "Border Collie", "Dachshund", "Bulldog Ingles", "Pug", "Chihuahua", "Akita", "Cocker Spaniel",
    "Lhasa Apso", "Boxer", "Doberman", "Schnauzer", "Basset Hound", "Husky Siberiano",
    "American Bully", "Pit Bull", "Fila Brasileiro", "Mastiff", "Bengal", "Angora", "Abissinio",
    "Noruegues da Floresta", "Scottish Fold", "Exotico", "Birman", "Himalayo", "Devon Rex",
    "Cornish Rex", "Bombay", "Sagrado da Birmania", "Lop", "Calopsita",
)
MESES_PT = {
    1: "Janeiro", 2: "Fevereiro", 3: "Marco", 4: "Abril", 5: "Maio", 6: "Junho",
    7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro",
}

app = Flask(__name__)
app.config["SECRET_KEY"] = "univet-chave-inicial-dev"


def get_db_connection():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON;")
    return connection


def login_obrigatorio(view_function):
    @wraps(view_function)
    def wrapped_view(*args, **kwargs):
        if "usuario_id" not in session:
            flash("Use o codigo de acesso para entrar no sistema.", "erro")
            return redirect(url_for("login"))
        return view_function(*args, **kwargs)

    return wrapped_view


def slugify_status(texto):
    texto_sem_acentos = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    return texto_sem_acentos.lower().replace(" ", "-")


def limpar_cpf(cpf):
    return "".join(caractere for caractere in cpf if caractere.isdigit())


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


def formatar_data_hora_br(valor):
    if not valor:
        return ""
    try:
        return datetime.strptime(valor, "%Y-%m-%dT%H:%M").strftime("%d/%m/%Y %H:%M")
    except ValueError:
        return valor.replace("T", " ")


def formatar_hora_br(valor):
    if not valor:
        return ""
    try:
        return datetime.strptime(valor, "%Y-%m-%dT%H:%M").strftime("%H:%M")
    except ValueError:
        return valor[11:16]


def formatar_data_br(valor):
    try:
        return datetime.strptime(valor, "%Y-%m-%d").strftime("%d/%m/%Y")
    except ValueError:
        return valor


def proximo_mes(ano, mes):
    return (ano + 1, 1) if mes == 12 else (ano, mes + 1)


def mes_anterior(ano, mes):
    return (ano - 1, 12) if mes == 1 else (ano, mes - 1)


def breadcrumbs_padrao(*itens):
    return [("Pagina inicial", url_for("pagina_inicial")), *itens]


def buscar_usuario_principal():
    connection = get_db_connection()
    usuario = connection.execute("SELECT * FROM usuarios ORDER BY id ASC LIMIT 1").fetchone()
    connection.close()
    return usuario


def buscar_tutores(termo_busca=""):
    connection = get_db_connection()
    if termo_busca:
        filtro = f"%{termo_busca}%"
        tutores = connection.execute(
            """
            SELECT *
            FROM tutores
            WHERE nome LIKE ? OR telefone LIKE ? OR cpf LIKE ? OR endereco LIKE ?
            ORDER BY nome ASC
            """,
            (filtro, filtro, filtro, filtro),
        ).fetchall()
    else:
        tutores = connection.execute("SELECT * FROM tutores ORDER BY nome ASC").fetchall()
    connection.close()
    return tutores


def buscar_pets(termo_busca=""):
    connection = get_db_connection()
    if termo_busca:
        filtro = f"%{termo_busca}%"
        pets = connection.execute(
            """
            SELECT pets.*, tutores.nome AS tutor_nome
            FROM pets
            INNER JOIN tutores ON tutores.id = pets.tutor_id
            WHERE pets.nome LIKE ? OR pets.especie LIKE ? OR pets.raca LIKE ? OR tutores.nome LIKE ?
            ORDER BY pets.nome ASC
            """,
            (filtro, filtro, filtro, filtro),
        ).fetchall()
    else:
        pets = connection.execute(
            """
            SELECT pets.*, tutores.nome AS tutor_nome
            FROM pets
            INNER JOIN tutores ON tutores.id = pets.tutor_id
            ORDER BY pets.nome ASC
            """
        ).fetchall()
    connection.close()
    return pets


def buscar_consultas_do_mes(ano, mes):
    connection = get_db_connection()
    prefixo = f"{ano:04d}-{mes:02d}"
    consultas = connection.execute(
        """
        SELECT consultas.*, pets.nome AS pet_nome, tutores.nome AS tutor_nome
        FROM consultas
        INNER JOIN pets ON pets.id = consultas.pet_id
        INNER JOIN tutores ON tutores.id = pets.tutor_id
        WHERE substr(consultas.data_hora, 1, 7) = ?
        ORDER BY consultas.data_hora ASC
        """,
        (prefixo,),
    ).fetchall()
    connection.close()
    return consultas


def buscar_consultas_do_dia(data_iso):
    connection = get_db_connection()
    consultas = connection.execute(
        """
        SELECT consultas.*, pets.nome AS pet_nome, tutores.nome AS tutor_nome
        FROM consultas
        INNER JOIN pets ON pets.id = consultas.pet_id
        INNER JOIN tutores ON tutores.id = pets.tutor_id
        WHERE date(consultas.data_hora) = ?
        ORDER BY consultas.data_hora ASC
        """,
        (data_iso,),
    ).fetchall()
    connection.close()
    return consultas


def montar_calendario_mensal(ano, mes):
    consultas_mes = buscar_consultas_do_mes(ano, mes)
    totais_por_dia = {}
    for consulta in consultas_mes:
        chave = consulta["data_hora"][:10]
        totais_por_dia[chave] = totais_por_dia.get(chave, 0) + 1

    calendario = Calendar(firstweekday=0)
    semanas = []
    for semana in calendario.monthdatescalendar(ano, mes):
        dias_semana = []
        for dia in semana:
            data_iso = dia.isoformat()
            dias_semana.append(
                {
                    "numero": dia.day,
                    "data_iso": data_iso,
                    "esta_no_mes": dia.month == mes,
                    "sem_expediente": dia.weekday() >= 5,
                    "total_consultas": totais_por_dia.get(data_iso, 0),
                    "tem_consultas": totais_por_dia.get(data_iso, 0) > 0,
                }
            )
        semanas.append(dias_semana)
    return semanas


def contar_consultas_por_status(consultas):
    resumo = {"Agendada": 0, "Concluida": 0, "Cancelada": 0}
    for consulta in consultas:
        if consulta["status"] in resumo:
            resumo[consulta["status"]] += 1
    return resumo


@app.context_processor
def inject_now():
    return {"agora": datetime.now(), "logo_url": url_for("static", filename="logo-clinica.jpg")}


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
        codigo_digitado = request.form.get("codigo_acesso", "").strip()
        if not codigo_digitado:
            flash("Digite o codigo de acesso para entrar.", "erro")
            return render_template("login.html")

        usuario = buscar_usuario_principal()
        if usuario and usuario["access_code_hash"] and check_password_hash(usuario["access_code_hash"], codigo_digitado):
            session["usuario_id"] = usuario["id"]
            session["usuario_login"] = usuario["login"]
            flash("Acesso liberado com sucesso.", "sucesso")
            return redirect(url_for("pagina_inicial"))

        flash("Codigo de acesso invalido.", "erro")

    return render_template("login.html")


@app.route("/pagina-inicial")
@login_obrigatorio
def pagina_inicial():
    connection = get_db_connection()
    hoje = datetime.now().strftime("%Y-%m-%d")
    consultas_hoje = connection.execute(
        """
        SELECT consultas.*, pets.nome AS pet_nome, tutores.nome AS tutor_nome
        FROM consultas
        INNER JOIN pets ON pets.id = consultas.pet_id
        INNER JOIN tutores ON tutores.id = pets.tutor_id
        WHERE date(consultas.data_hora) = ?
        ORDER BY consultas.data_hora ASC
        """,
        (hoje,),
    ).fetchall()

    totais = {
        "tutores": connection.execute("SELECT COUNT(*) FROM tutores").fetchone()[0],
        "pets": connection.execute("SELECT COUNT(*) FROM pets").fetchone()[0],
        "consultas": connection.execute("SELECT COUNT(*) FROM consultas").fetchone()[0],
    }
    proximas_consultas = connection.execute(
        """
        SELECT consultas.*, pets.nome AS pet_nome, tutores.nome AS tutor_nome
        FROM consultas
        INNER JOIN pets ON pets.id = consultas.pet_id
        INNER JOIN tutores ON tutores.id = pets.tutor_id
        WHERE consultas.data_hora >= ?
        ORDER BY consultas.data_hora ASC
        LIMIT 5
        """,
        (datetime.now().strftime("%Y-%m-%dT%H:%M"),),
    ).fetchall()
    connection.close()

    return render_template(
        "pagina_inicial.html",
        consultas_hoje=consultas_hoje,
        proximas_consultas=proximas_consultas,
        resumo_hoje=contar_consultas_por_status(consultas_hoje),
        totais=totais,
        secao="pagina_inicial",
        breadcrumbs=[("Pagina inicial", None)],
    )


@app.route("/tutores")
@login_obrigatorio
def listar_tutores():
    busca = request.args.get("busca", "").strip()
    return render_template(
        "tutores/lista.html",
        tutores=buscar_tutores(busca),
        busca=busca,
        secao="tutores",
        breadcrumbs=breadcrumbs_padrao(("Tutores", None)),
    )


@app.route("/tutores/novo", methods=["GET", "POST"])
@login_obrigatorio
def criar_tutor():
    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        telefone = request.form.get("telefone", "").strip()
        cpf = request.form.get("cpf", "").strip()
        endereco = request.form.get("endereco", "").strip()
        tutor_form = {"nome": nome, "telefone": telefone, "cpf": cpf, "endereco": endereco}

        if not nome or not telefone or not cpf:
            flash("Nome, telefone e CPF do tutor sao obrigatorios.", "erro")
            return render_template("tutores/form.html", tutor=tutor_form, acao="Novo Tutor", secao="tutores", breadcrumbs=breadcrumbs_padrao(("Tutores", url_for("listar_tutores")), ("Novo tutor", None)))

        if not validar_cpf(cpf):
            flash("Informe um CPF valido no formato XXX.XXX.XXX-XX.", "erro")
            return render_template("tutores/form.html", tutor=tutor_form, acao="Novo Tutor", secao="tutores", breadcrumbs=breadcrumbs_padrao(("Tutores", url_for("listar_tutores")), ("Novo tutor", None)))

        connection = get_db_connection()
        try:
            connection.execute("INSERT INTO tutores (nome, telefone, cpf, endereco) VALUES (?, ?, ?, ?)", (nome, telefone, formatar_cpf(cpf), endereco))
            connection.commit()
        except sqlite3.IntegrityError:
            connection.close()
            flash("Ja existe um tutor cadastrado com este CPF.", "erro")
            return render_template("tutores/form.html", tutor=tutor_form, acao="Novo Tutor", secao="tutores", breadcrumbs=breadcrumbs_padrao(("Tutores", url_for("listar_tutores")), ("Novo tutor", None)))
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
        flash("Tutor nao encontrado.", "erro")
        return redirect(url_for("listar_tutores"))

    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        telefone = request.form.get("telefone", "").strip()
        cpf = request.form.get("cpf", "").strip()
        endereco = request.form.get("endereco", "").strip()
        tutor_form = {"id": tutor_id, "nome": nome, "telefone": telefone, "cpf": cpf, "endereco": endereco}

        if not nome or not telefone or not cpf:
            flash("Nome, telefone e CPF do tutor sao obrigatorios.", "erro")
            return render_template("tutores/form.html", tutor=tutor_form, acao="Editar Tutor", secao="tutores", breadcrumbs=breadcrumbs_padrao(("Tutores", url_for("listar_tutores")), ("Editar tutor", None)))

        if not validar_cpf(cpf):
            flash("Informe um CPF valido no formato XXX.XXX.XXX-XX.", "erro")
            return render_template("tutores/form.html", tutor=tutor_form, acao="Editar Tutor", secao="tutores", breadcrumbs=breadcrumbs_padrao(("Tutores", url_for("listar_tutores")), ("Editar tutor", None)))

        connection = get_db_connection()
        try:
            connection.execute(
                "UPDATE tutores SET nome = ?, telefone = ?, cpf = ?, endereco = ? WHERE id = ?",
                (nome, telefone, formatar_cpf(cpf), endereco, tutor_id),
            )
            connection.commit()
        except sqlite3.IntegrityError:
            connection.close()
            flash("Ja existe outro tutor cadastrado com este CPF.", "erro")
            return render_template("tutores/form.html", tutor=tutor_form, acao="Editar Tutor", secao="tutores", breadcrumbs=breadcrumbs_padrao(("Tutores", url_for("listar_tutores")), ("Editar tutor", None)))
        connection.close()
        flash("Tutor atualizado com sucesso.", "sucesso")
        return redirect(url_for("listar_tutores"))

    return render_template("tutores/form.html", tutor=tutor, acao="Editar Tutor", secao="tutores", breadcrumbs=breadcrumbs_padrao(("Tutores", url_for("listar_tutores")), ("Editar tutor", None)))


@app.route("/tutores/<int:tutor_id>/excluir", methods=["POST"])
@login_obrigatorio
def excluir_tutor(tutor_id):
    connection = get_db_connection()
    pets_vinculados = connection.execute("SELECT COUNT(*) FROM pets WHERE tutor_id = ?", (tutor_id,)).fetchone()[0]
    if pets_vinculados > 0:
        connection.close()
        flash("Nao e possivel excluir um tutor que possui pets cadastrados.", "erro")
        return redirect(url_for("listar_tutores"))

    connection.execute("DELETE FROM tutores WHERE id = ?", (tutor_id,))
    connection.commit()
    connection.close()
    flash("Tutor excluido com sucesso.", "sucesso")
    return redirect(url_for("listar_tutores"))


@app.route("/pets")
@login_obrigatorio
def listar_pets():
    busca = request.args.get("busca", "").strip()
    return render_template("pets/lista.html", pets=buscar_pets(busca), busca=busca, secao="pets", breadcrumbs=breadcrumbs_padrao(("Pets", None)))


@app.route("/pets/novo", methods=["GET", "POST"])
@login_obrigatorio
def criar_pet():
    tutores = buscar_tutores()
    if not tutores:
        flash("Cadastre pelo menos um tutor antes de cadastrar pets.", "erro")
        return redirect(url_for("listar_tutores"))

    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        especie = request.form.get("especie", "").strip()
        raca_selecionada = request.form.get("raca_padrao", "").strip()
        raca_personalizada = request.form.get("raca_personalizada", "").strip()
        idade = request.form.get("idade", "").strip()
        tutor_id = request.form.get("tutor_id", "").strip()
        historico = request.form.get("historico", "").strip()
        raca_final = raca_personalizada if raca_selecionada == "Outra" else raca_selecionada
        pet_form = {"nome": nome, "especie": especie, "raca": raca_final, "raca_padrao": raca_selecionada, "raca_personalizada": raca_personalizada, "idade": idade, "tutor_id": tutor_id, "historico": historico}

        if not nome or not especie or not raca_final or not tutor_id:
            flash("Preencha os campos obrigatorios do pet.", "erro")
            return render_template("pets/form.html", pet=pet_form, tutores=tutores, especies_sugeridas=ESPECIES_SUGERIDAS, racas_comuns=RACAS_COMUNS, acao="Novo Pet", secao="pets", breadcrumbs=breadcrumbs_padrao(("Pets", url_for("listar_pets")), ("Novo pet", None)))

        connection = get_db_connection()
        try:
            connection.execute("INSERT INTO pets (nome, especie, raca, idade, tutor_id, historico) VALUES (?, ?, ?, ?, ?, ?)", (nome, especie, raca_final, idade, tutor_id, historico))
            connection.commit()
        except sqlite3.IntegrityError:
            connection.close()
            flash("Nao foi possivel salvar o pet. Verifique o tutor selecionado.", "erro")
            return render_template("pets/form.html", pet=pet_form, tutores=tutores, especies_sugeridas=ESPECIES_SUGERIDAS, racas_comuns=RACAS_COMUNS, acao="Novo Pet", secao="pets", breadcrumbs=breadcrumbs_padrao(("Pets", url_for("listar_pets")), ("Novo pet", None)))
        connection.close()
        flash("Pet cadastrado com sucesso.", "sucesso")
        return redirect(url_for("listar_pets"))

    return render_template("pets/form.html", pet=None, tutores=tutores, especies_sugeridas=ESPECIES_SUGERIDAS, racas_comuns=RACAS_COMUNS, acao="Novo Pet", secao="pets", breadcrumbs=breadcrumbs_padrao(("Pets", url_for("listar_pets")), ("Novo pet", None)))


@app.route("/pets/<int:pet_id>/editar", methods=["GET", "POST"])
@login_obrigatorio
def editar_pet(pet_id):
    connection = get_db_connection()
    pet = connection.execute("SELECT * FROM pets WHERE id = ?", (pet_id,)).fetchone()
    connection.close()

    if not pet:
        flash("Pet nao encontrado.", "erro")
        return redirect(url_for("listar_pets"))

    tutores = buscar_tutores()

    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        especie = request.form.get("especie", "").strip()
        raca_selecionada = request.form.get("raca_padrao", "").strip()
        raca_personalizada = request.form.get("raca_personalizada", "").strip()
        idade = request.form.get("idade", "").strip()
        tutor_id = request.form.get("tutor_id", "").strip()
        historico = request.form.get("historico", "").strip()
        raca_final = raca_personalizada if raca_selecionada == "Outra" else raca_selecionada
        pet_form = {"id": pet_id, "nome": nome, "especie": especie, "raca": raca_final, "raca_padrao": raca_selecionada, "raca_personalizada": raca_personalizada, "idade": idade, "tutor_id": tutor_id, "historico": historico}

        if not nome or not especie or not raca_final or not tutor_id:
            flash("Preencha os campos obrigatorios do pet.", "erro")
            return render_template("pets/form.html", pet=pet_form, tutores=tutores, especies_sugeridas=ESPECIES_SUGERIDAS, racas_comuns=RACAS_COMUNS, acao="Editar Pet", secao="pets", breadcrumbs=breadcrumbs_padrao(("Pets", url_for("listar_pets")), ("Editar pet", None)))

        connection = get_db_connection()
        try:
            connection.execute(
                "UPDATE pets SET nome = ?, especie = ?, raca = ?, idade = ?, tutor_id = ?, historico = ? WHERE id = ?",
                (nome, especie, raca_final, idade, tutor_id, historico, pet_id),
            )
            connection.commit()
        except sqlite3.IntegrityError:
            connection.close()
            flash("Nao foi possivel atualizar o pet. Verifique o tutor selecionado.", "erro")
            return render_template("pets/form.html", pet=pet_form, tutores=tutores, especies_sugeridas=ESPECIES_SUGERIDAS, racas_comuns=RACAS_COMUNS, acao="Editar Pet", secao="pets", breadcrumbs=breadcrumbs_padrao(("Pets", url_for("listar_pets")), ("Editar pet", None)))
        connection.close()
        flash("Pet atualizado com sucesso.", "sucesso")
        return redirect(url_for("listar_pets"))

    return render_template("pets/form.html", pet=pet, tutores=tutores, especies_sugeridas=ESPECIES_SUGERIDAS, racas_comuns=RACAS_COMUNS, acao="Editar Pet", secao="pets", breadcrumbs=breadcrumbs_padrao(("Pets", url_for("listar_pets")), ("Editar pet", None)))


@app.route("/pets/<int:pet_id>/excluir", methods=["POST"])
@login_obrigatorio
def excluir_pet(pet_id):
    connection = get_db_connection()
    consultas_vinculadas = connection.execute("SELECT COUNT(*) FROM consultas WHERE pet_id = ?", (pet_id,)).fetchone()[0]
    if consultas_vinculadas > 0:
        connection.close()
        flash("Nao e possivel excluir um pet que possui consultas cadastradas.", "erro")
        return redirect(url_for("listar_pets"))

    connection.execute("DELETE FROM pets WHERE id = ?", (pet_id,))
    connection.commit()
    connection.close()
    flash("Pet excluido com sucesso.", "sucesso")
    return redirect(url_for("listar_pets"))


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
        calendario=montar_calendario_mensal(ano, mes),
        consultas_mes=buscar_consultas_do_mes(ano, mes)[:8],
        ano=ano,
        mes=mes,
        nome_mes=MESES_PT.get(mes, str(mes)),
        ano_anterior=ano_anterior,
        mes_anterior=mes_anterior_valor,
        ano_proximo=ano_proximo,
        mes_proximo=mes_proximo_valor,
        secao="consultas",
        breadcrumbs=breadcrumbs_padrao(("Consultas", None)),
    )


@app.route("/consultas/dia/<data_iso>")
@login_obrigatorio
def agenda_do_dia(data_iso):
    return render_template(
        "consultas/dia.html",
        consultas=buscar_consultas_do_dia(data_iso),
        data_iso=data_iso,
        secao="consultas",
        breadcrumbs=breadcrumbs_padrao(("Consultas", url_for("listar_consultas")), ("Agenda do dia", None)),
    )


@app.route("/consultas/nova", methods=["GET", "POST"])
@login_obrigatorio
def criar_consulta():
    pets = buscar_pets()
    if not pets:
        flash("Cadastre pelo menos um pet antes de agendar consultas.", "erro")
        return redirect(url_for("listar_pets"))

    if request.method == "POST":
        data_hora = request.form.get("data_hora", "").strip()
        pet_id = request.form.get("pet_id", "").strip()
        tipo_consulta = request.form.get("tipo_consulta", "").strip()
        confirmacao_status = request.form.get("confirmacao_status", "").strip()
        observacoes = request.form.get("observacoes", "").strip()
        status = request.form.get("status", "Agendada").strip()
        consulta_form = {"data_hora": data_hora, "pet_id": pet_id, "tipo_consulta": tipo_consulta, "confirmacao_status": confirmacao_status, "observacoes": observacoes, "status": status}

        if not data_hora or not pet_id or not tipo_consulta or not confirmacao_status or not status:
            flash("Preencha os campos obrigatorios da consulta.", "erro")
            return render_template("consultas/form.html", consulta=consulta_form, pets=pets, tipos_consulta=TIPOS_CONSULTA, status_confirmacao=STATUSS_CONFIRMACAO, acao="Nova Consulta", secao="consultas", breadcrumbs=breadcrumbs_padrao(("Consultas", url_for("listar_consultas")), ("Nova consulta", None)))

        if status not in STATUSS_CONSULTA or confirmacao_status not in STATUSS_CONFIRMACAO:
            flash("Selecione valores validos para status e confirmacao.", "erro")
            return render_template("consultas/form.html", consulta=consulta_form, pets=pets, tipos_consulta=TIPOS_CONSULTA, status_confirmacao=STATUSS_CONFIRMACAO, acao="Nova Consulta", secao="consultas", breadcrumbs=breadcrumbs_padrao(("Consultas", url_for("listar_consultas")), ("Nova consulta", None)))

        connection = get_db_connection()
        try:
            connection.execute(
                "INSERT INTO consultas (data_hora, pet_id, tipo_consulta, observacoes, status, confirmacao_status) VALUES (?, ?, ?, ?, ?, ?)",
                (data_hora, pet_id, tipo_consulta, observacoes, status, confirmacao_status),
            )
            connection.commit()
        except sqlite3.IntegrityError:
            connection.close()
            flash("Nao foi possivel salvar a consulta. Verifique o pet selecionado.", "erro")
            return render_template("consultas/form.html", consulta=consulta_form, pets=pets, tipos_consulta=TIPOS_CONSULTA, status_confirmacao=STATUSS_CONFIRMACAO, acao="Nova Consulta", secao="consultas", breadcrumbs=breadcrumbs_padrao(("Consultas", url_for("listar_consultas")), ("Nova consulta", None)))
        connection.close()
        flash("Consulta agendada com sucesso.", "sucesso")
        return redirect(url_for("listar_consultas"))

    return render_template("consultas/form.html", consulta=None, pets=pets, tipos_consulta=TIPOS_CONSULTA, status_confirmacao=STATUSS_CONFIRMACAO, acao="Nova Consulta", secao="consultas", breadcrumbs=breadcrumbs_padrao(("Consultas", url_for("listar_consultas")), ("Nova consulta", None)))


@app.route("/consultas/<int:consulta_id>/editar", methods=["GET", "POST"])
@login_obrigatorio
def editar_consulta(consulta_id):
    connection = get_db_connection()
    consulta = connection.execute("SELECT * FROM consultas WHERE id = ?", (consulta_id,)).fetchone()
    connection.close()
    if not consulta:
        flash("Consulta nao encontrada.", "erro")
        return redirect(url_for("listar_consultas"))

    pets = buscar_pets()
    if request.method == "POST":
        data_hora = request.form.get("data_hora", "").strip()
        pet_id = request.form.get("pet_id", "").strip()
        tipo_consulta = request.form.get("tipo_consulta", "").strip()
        confirmacao_status = request.form.get("confirmacao_status", "").strip()
        observacoes = request.form.get("observacoes", "").strip()
        status = request.form.get("status", "").strip()
        consulta_form = {"id": consulta_id, "data_hora": data_hora, "pet_id": pet_id, "tipo_consulta": tipo_consulta, "confirmacao_status": confirmacao_status, "observacoes": observacoes, "status": status}

        if not data_hora or not pet_id or not tipo_consulta or not confirmacao_status or not status:
            flash("Preencha os campos obrigatorios da consulta.", "erro")
            return render_template("consultas/form.html", consulta=consulta_form, pets=pets, tipos_consulta=TIPOS_CONSULTA, status_confirmacao=STATUSS_CONFIRMACAO, acao="Editar Consulta", secao="consultas", breadcrumbs=breadcrumbs_padrao(("Consultas", url_for("listar_consultas")), ("Editar consulta", None)))

        if status not in STATUSS_CONSULTA or confirmacao_status not in STATUSS_CONFIRMACAO:
            flash("Selecione valores validos para status e confirmacao.", "erro")
            return render_template("consultas/form.html", consulta=consulta_form, pets=pets, tipos_consulta=TIPOS_CONSULTA, status_confirmacao=STATUSS_CONFIRMACAO, acao="Editar Consulta", secao="consultas", breadcrumbs=breadcrumbs_padrao(("Consultas", url_for("listar_consultas")), ("Editar consulta", None)))

        connection = get_db_connection()
        try:
            connection.execute(
                "UPDATE consultas SET data_hora = ?, pet_id = ?, tipo_consulta = ?, observacoes = ?, status = ?, confirmacao_status = ? WHERE id = ?",
                (data_hora, pet_id, tipo_consulta, observacoes, status, confirmacao_status, consulta_id),
            )
            connection.commit()
        except sqlite3.IntegrityError:
            connection.close()
            flash("Nao foi possivel atualizar a consulta. Verifique o pet selecionado.", "erro")
            return render_template("consultas/form.html", consulta=consulta_form, pets=pets, tipos_consulta=TIPOS_CONSULTA, status_confirmacao=STATUSS_CONFIRMACAO, acao="Editar Consulta", secao="consultas", breadcrumbs=breadcrumbs_padrao(("Consultas", url_for("listar_consultas")), ("Editar consulta", None)))
        connection.close()
        flash("Consulta atualizada com sucesso.", "sucesso")
        return redirect(url_for("listar_consultas"))

    return render_template("consultas/form.html", consulta=consulta, pets=pets, tipos_consulta=TIPOS_CONSULTA, status_confirmacao=STATUSS_CONFIRMACAO, acao="Editar Consulta", secao="consultas", breadcrumbs=breadcrumbs_padrao(("Consultas", url_for("listar_consultas")), ("Editar consulta", None)))


@app.route("/consultas/<int:consulta_id>/excluir", methods=["POST"])
@login_obrigatorio
def excluir_consulta(consulta_id):
    connection = get_db_connection()
    connection.execute("DELETE FROM consultas WHERE id = ?", (consulta_id,))
    connection.commit()
    connection.close()
    flash("Consulta excluida com sucesso.", "sucesso")
    return redirect(url_for("listar_consultas"))


@app.route("/logout")
def logout():
    session.clear()
    flash("Sessao encerrada com sucesso.", "sucesso")
    return redirect(url_for("login"))


@app.errorhandler(404)
def pagina_nao_encontrada(error):
    if "usuario_id" not in session:
        return redirect(url_for("login"))
    flash("A pagina solicitada nao foi encontrada.", "erro")
    return redirect(url_for("pagina_inicial"))


if __name__ == "__main__":
    app.run(debug=True)
