from flask import flash, redirect, render_template, request, session, url_for

from .base import main
from ..models import Usuario


@main.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        senha = request.form.get("senha") or ""

        usuario = Usuario.query.filter_by(email=email).first()

        if not usuario:
            flash("Email ou senha inválidos.", "error")
            return redirect(url_for("main.login"))

        if not usuario.ativo:
            flash("Usuário inativo. Entre em contato com o administrador.", "error")
            return redirect(url_for("main.login"))

        if usuario.check_password(senha):
            session["usuario_id"] = usuario.id
            session["perfil"] = usuario.perfil
            session["cliente_id"] = usuario.cliente_id

            return redirect(url_for("main.painel"))

        flash("Email ou senha inválidos.", "error")
        return redirect(url_for("main.login"))

    return render_template("login.html")


@main.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("main.login"))