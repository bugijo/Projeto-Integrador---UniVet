from datetime import datetime
from functools import wraps
from pathlib import Path
import sqlite3

from flask import Flask, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash


BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "banco.db"

app = Flask(__name__)
app.config["SECRET_KEY"] = "univet-chave-inicial-dev"


def get_db_connection():
    """Abre uma conexao com o SQLite e permite acessar colunas pelo nome."""
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON;")
    return connection


def login_obrigatorio(view_function):
    """Bloqueia o acesso a rotas internas quando a usuaria nao fez login."""

    @wraps(view_function)
    def wrapped_view(*args, **kwargs):
        if "usuario_id" not in session:
            flash("Faça login para acessar o sistema.", "erro")
            return redirect(url_for("login"))
        return view_function(*args, **kwargs)

    return wrapped_view


def buscar_tutores(termo_busca=""):
    """Lista tutores e permite filtrar pelo nome ou telefone."""
    connection = get_db_connection()
    if termo_busca:
        filtro = f"%{termo_busca}%"
        tutores = connection.execute(
            """
            SELECT *
            FROM tutores
            WHERE nome LIKE ? OR telefone LIKE ? OR endereco LIKE ?
            ORDER BY nome ASC
            """,
            (filtro, filtro, filtro),
        ).fetchall()
    else:
        tutores = connection.execute(
            "SELECT * FROM tutores ORDER BY nome ASC"
        ).fetchall()
    connection.close()
    return tutores


def buscar_pets(termo_busca=""):
    """Lista pets com o nome do tutor vinculado e permite filtro simples."""
    connection = get_db_connection()
    if termo_busca:
        filtro = f"%{termo_busca}%"
        pets = connection.execute(
            """
            SELECT pets.*, tutores.nome AS tutor_nome
            FROM pets
            INNER JOIN tutores ON tutores.id = pets.tutor_id
            WHERE pets.nome LIKE ?
               OR pets.especie LIKE ?
               OR pets.raca LIKE ?
               OR tutores.nome LIKE ?
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


def buscar_consultas(termo_busca="", status=""):
    """Lista consultas com informacoes do pet e do tutor e aplica filtros."""
    connection = get_db_connection()
    filtros = []
    parametros = []

    if termo_busca:
        filtros.append("(pets.nome LIKE ? OR tutores.nome LIKE ? OR consultas.data_hora LIKE ?)")
        filtro = f"%{termo_busca}%"
        parametros.extend([filtro, filtro, filtro])

    if status:
        filtros.append("consultas.status = ?")
        parametros.append(status)

    sql = """
        SELECT
            consultas.*,
            pets.nome AS pet_nome,
            tutores.nome AS tutor_nome
        FROM consultas
        INNER JOIN pets ON pets.id = consultas.pet_id
        INNER JOIN tutores ON tutores.id = pets.tutor_id
    """

    if filtros:
        sql += " WHERE " + " AND ".join(filtros)

    sql += " ORDER BY consultas.data_hora ASC"
    consultas = connection.execute(sql, parametros).fetchall()
    connection.close()
    return consultas


@app.context_processor
def inject_now():
    """Envia a data atual para os templates internos do sistema."""
    return {"agora": datetime.now()}


@app.route("/", methods=["GET", "POST"])
@app.route("/login", methods=["GET", "POST"])
def login():
    """Exibe a tela de login e valida o acesso da proprietaria."""
    if "usuario_id" in session:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        login_digitado = request.form.get("login", "").strip()
        senha_digitada = request.form.get("senha", "").strip()

        if not login_digitado or not senha_digitada:
            flash("Preencha usuario e senha para continuar.", "erro")
            return render_template("login.html")

        connection = get_db_connection()
        usuario = connection.execute(
            "SELECT * FROM usuarios WHERE login = ?",
            (login_digitado,),
        ).fetchone()
        connection.close()

        if usuario and check_password_hash(usuario["senha_hash"], senha_digitada):
            session["usuario_id"] = usuario["id"]
            session["usuario_login"] = usuario["login"]
            flash("Login realizado com sucesso.", "sucesso")
            return redirect(url_for("dashboard"))

        flash("Usuario ou senha invalidos.", "erro")

    return render_template("login.html")


@app.route("/dashboard")
@login_obrigatorio
def dashboard():
    """Mostra a agenda do dia com resumo rapido do sistema."""
    connection = get_db_connection()
    hoje = datetime.now().strftime("%Y-%m-%d")

    consultas_hoje = connection.execute(
        """
        SELECT
            consultas.*,
            pets.nome AS pet_nome,
            tutores.nome AS tutor_nome
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
    connection.close()

    return render_template(
        "dashboard.html",
        consultas_hoje=consultas_hoje,
        totais=totais,
        secao="dashboard",
    )


@app.route("/tutores")
@login_obrigatorio
def listar_tutores():
    """Exibe a lista de tutores cadastrados."""
    busca = request.args.get("busca", "").strip()
    return render_template(
        "tutores/lista.html",
        tutores=buscar_tutores(busca),
        busca=busca,
        secao="tutores",
    )


@app.route("/tutores/novo", methods=["GET", "POST"])
@login_obrigatorio
def criar_tutor():
    """Cadastra um novo tutor no sistema."""
    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        telefone = request.form.get("telefone", "").strip()
        endereco = request.form.get("endereco", "").strip()

        if not nome or not telefone:
            flash("Nome e telefone do tutor sao obrigatorios.", "erro")
            return render_template(
                "tutores/form.html",
                tutor={"nome": nome, "telefone": telefone, "endereco": endereco},
                acao="Novo Tutor",
                secao="tutores",
            )

        connection = get_db_connection()
        connection.execute(
            "INSERT INTO tutores (nome, telefone, endereco) VALUES (?, ?, ?)",
            (nome, telefone, endereco),
        )
        connection.commit()
        connection.close()

        flash("Tutor cadastrado com sucesso.", "sucesso")
        return redirect(url_for("listar_tutores"))

    return render_template("tutores/form.html", tutor=None, acao="Novo Tutor", secao="tutores")


@app.route("/tutores/<int:tutor_id>/editar", methods=["GET", "POST"])
@login_obrigatorio
def editar_tutor(tutor_id):
    """Atualiza os dados de um tutor ja existente."""
    connection = get_db_connection()
    tutor = connection.execute(
        "SELECT * FROM tutores WHERE id = ?",
        (tutor_id,),
    ).fetchone()

    if not tutor:
        connection.close()
        flash("Tutor nao encontrado.", "erro")
        return redirect(url_for("listar_tutores"))

    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        telefone = request.form.get("telefone", "").strip()
        endereco = request.form.get("endereco", "").strip()

        if not nome or not telefone:
            connection.close()
            flash("Nome e telefone do tutor sao obrigatorios.", "erro")
            return render_template(
                "tutores/form.html",
                tutor={"id": tutor_id, "nome": nome, "telefone": telefone, "endereco": endereco},
                acao="Editar Tutor",
                secao="tutores",
            )

        connection.execute(
            """
            UPDATE tutores
            SET nome = ?, telefone = ?, endereco = ?
            WHERE id = ?
            """,
            (nome, telefone, endereco, tutor_id),
        )
        connection.commit()
        connection.close()

        flash("Tutor atualizado com sucesso.", "sucesso")
        return redirect(url_for("listar_tutores"))

    connection.close()
    return render_template("tutores/form.html", tutor=tutor, acao="Editar Tutor", secao="tutores")


@app.route("/tutores/<int:tutor_id>/excluir", methods=["POST"])
@login_obrigatorio
def excluir_tutor(tutor_id):
    """Exclui um tutor apenas quando ele nao possui pets vinculados."""
    connection = get_db_connection()
    pets_vinculados = connection.execute(
        "SELECT COUNT(*) FROM pets WHERE tutor_id = ?",
        (tutor_id,),
    ).fetchone()[0]

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
    """Exibe a lista de pets com seus respectivos tutores."""
    busca = request.args.get("busca", "").strip()
    return render_template(
        "pets/lista.html",
        pets=buscar_pets(busca),
        busca=busca,
        secao="pets",
    )


@app.route("/pets/novo", methods=["GET", "POST"])
@login_obrigatorio
def criar_pet():
    """Cadastra um novo pet vinculado a um tutor."""
    tutores = buscar_tutores()

    if not tutores:
        flash("Cadastre pelo menos um tutor antes de cadastrar pets.", "erro")
        return redirect(url_for("listar_tutores"))

    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        especie = request.form.get("especie", "").strip()
        raca = request.form.get("raca", "").strip()
        idade = request.form.get("idade", "").strip()
        tutor_id = request.form.get("tutor_id", "").strip()
        historico = request.form.get("historico", "").strip()

        if not nome or not especie or not raca or not tutor_id:
            flash("Preencha os campos obrigatorios do pet.", "erro")
            return render_template(
                "pets/form.html",
                pet={
                    "nome": nome,
                    "especie": especie,
                    "raca": raca,
                    "idade": idade,
                    "tutor_id": tutor_id,
                    "historico": historico,
                },
                tutores=tutores,
                acao="Novo Pet",
                secao="pets",
            )

        connection = get_db_connection()
        connection.execute(
            """
            INSERT INTO pets (nome, especie, raca, idade, tutor_id, historico)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (nome, especie, raca, idade, tutor_id, historico),
        )
        connection.commit()
        connection.close()

        flash("Pet cadastrado com sucesso.", "sucesso")
        return redirect(url_for("listar_pets"))

    return render_template("pets/form.html", pet=None, tutores=tutores, acao="Novo Pet", secao="pets")


@app.route("/pets/<int:pet_id>/editar", methods=["GET", "POST"])
@login_obrigatorio
def editar_pet(pet_id):
    """Atualiza os dados de um pet existente."""
    connection = get_db_connection()
    pet = connection.execute(
        "SELECT * FROM pets WHERE id = ?",
        (pet_id,),
    ).fetchone()
    connection.close()

    if not pet:
        flash("Pet nao encontrado.", "erro")
        return redirect(url_for("listar_pets"))

    tutores = buscar_tutores()

    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        especie = request.form.get("especie", "").strip()
        raca = request.form.get("raca", "").strip()
        idade = request.form.get("idade", "").strip()
        tutor_id = request.form.get("tutor_id", "").strip()
        historico = request.form.get("historico", "").strip()

        if not nome or not especie or not raca or not tutor_id:
            flash("Preencha os campos obrigatorios do pet.", "erro")
            return render_template(
                "pets/form.html",
                pet={
                    "id": pet_id,
                    "nome": nome,
                    "especie": especie,
                    "raca": raca,
                    "idade": idade,
                    "tutor_id": tutor_id,
                    "historico": historico,
                },
                tutores=tutores,
                acao="Editar Pet",
                secao="pets",
            )

        connection = get_db_connection()
        connection.execute(
            """
            UPDATE pets
            SET nome = ?, especie = ?, raca = ?, idade = ?, tutor_id = ?, historico = ?
            WHERE id = ?
            """,
            (nome, especie, raca, idade, tutor_id, historico, pet_id),
        )
        connection.commit()
        connection.close()

        flash("Pet atualizado com sucesso.", "sucesso")
        return redirect(url_for("listar_pets"))

    return render_template("pets/form.html", pet=pet, tutores=tutores, acao="Editar Pet", secao="pets")


@app.route("/pets/<int:pet_id>/excluir", methods=["POST"])
@login_obrigatorio
def excluir_pet(pet_id):
    """Exclui um pet apenas quando ele nao possui consultas vinculadas."""
    connection = get_db_connection()
    consultas_vinculadas = connection.execute(
        "SELECT COUNT(*) FROM consultas WHERE pet_id = ?",
        (pet_id,),
    ).fetchone()[0]

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
    """Exibe todas as consultas cadastradas no sistema."""
    busca = request.args.get("busca", "").strip()
    status = request.args.get("status", "").strip()
    return render_template(
        "consultas/lista.html",
        consultas=buscar_consultas(busca, status),
        busca=busca,
        status=status,
        secao="consultas",
    )


@app.route("/consultas/nova", methods=["GET", "POST"])
@login_obrigatorio
def criar_consulta():
    """Agenda uma nova consulta para um pet cadastrado."""
    pets = buscar_pets()

    if not pets:
        flash("Cadastre pelo menos um pet antes de agendar consultas.", "erro")
        return redirect(url_for("listar_pets"))

    if request.method == "POST":
        data_hora = request.form.get("data_hora", "").strip()
        pet_id = request.form.get("pet_id", "").strip()
        observacoes = request.form.get("observacoes", "").strip()
        status = request.form.get("status", "Agendada").strip()

        if not data_hora or not pet_id or not status:
            flash("Preencha os campos obrigatorios da consulta.", "erro")
            return render_template(
                "consultas/form.html",
                consulta={
                    "data_hora": data_hora,
                    "pet_id": pet_id,
                    "observacoes": observacoes,
                    "status": status,
                },
                pets=pets,
                acao="Nova Consulta",
                secao="consultas",
            )

        connection = get_db_connection()
        connection.execute(
            """
            INSERT INTO consultas (data_hora, pet_id, observacoes, status)
            VALUES (?, ?, ?, ?)
            """,
            (data_hora, pet_id, observacoes, status),
        )
        connection.commit()
        connection.close()

        flash("Consulta agendada com sucesso.", "sucesso")
        return redirect(url_for("listar_consultas"))

    return render_template("consultas/form.html", consulta=None, pets=pets, acao="Nova Consulta", secao="consultas")


@app.route("/consultas/<int:consulta_id>/editar", methods=["GET", "POST"])
@login_obrigatorio
def editar_consulta(consulta_id):
    """Atualiza data, pet, observacoes e status de uma consulta."""
    connection = get_db_connection()
    consulta = connection.execute(
        "SELECT * FROM consultas WHERE id = ?",
        (consulta_id,),
    ).fetchone()
    connection.close()

    if not consulta:
        flash("Consulta nao encontrada.", "erro")
        return redirect(url_for("listar_consultas"))

    pets = buscar_pets()

    if request.method == "POST":
        data_hora = request.form.get("data_hora", "").strip()
        pet_id = request.form.get("pet_id", "").strip()
        observacoes = request.form.get("observacoes", "").strip()
        status = request.form.get("status", "").strip()

        if not data_hora or not pet_id or not status:
            flash("Preencha os campos obrigatorios da consulta.", "erro")
            return render_template(
                "consultas/form.html",
                consulta={
                    "id": consulta_id,
                    "data_hora": data_hora,
                    "pet_id": pet_id,
                    "observacoes": observacoes,
                    "status": status,
                },
                pets=pets,
                acao="Editar Consulta",
                secao="consultas",
            )

        connection = get_db_connection()
        connection.execute(
            """
            UPDATE consultas
            SET data_hora = ?, pet_id = ?, observacoes = ?, status = ?
            WHERE id = ?
            """,
            (data_hora, pet_id, observacoes, status, consulta_id),
        )
        connection.commit()
        connection.close()

        flash("Consulta atualizada com sucesso.", "sucesso")
        return redirect(url_for("listar_consultas"))

    return render_template("consultas/form.html", consulta=consulta, pets=pets, acao="Editar Consulta", secao="consultas")


@app.route("/consultas/<int:consulta_id>/excluir", methods=["POST"])
@login_obrigatorio
def excluir_consulta(consulta_id):
    """Remove uma consulta quando ela nao e mais necessaria."""
    connection = get_db_connection()
    connection.execute("DELETE FROM consultas WHERE id = ?", (consulta_id,))
    connection.commit()
    connection.close()

    flash("Consulta excluida com sucesso.", "sucesso")
    return redirect(url_for("listar_consultas"))


@app.route("/logout")
def logout():
    """Encerra a sessao atual da usuaria."""
    session.clear()
    flash("Sessao encerrada com sucesso.", "sucesso")
    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(debug=True)
