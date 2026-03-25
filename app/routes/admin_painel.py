from flask import redirect, render_template, url_for

from .base import main
from ..helpers.auth import obter_usuario_logado
from ..helpers.decorators import login_obrigatorio


@main.route("/admin")
@login_obrigatorio
def admin_painel():
    usuario = obter_usuario_logado()

    if not usuario or usuario.perfil != "admin":
        return redirect(url_for("main.painel"))

    return render_template("admin_painel.html")