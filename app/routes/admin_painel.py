from flask import render_template

from .base import main
from ..helpers.auth import obter_usuario_logado
from ..helpers.decorators import login_obrigatorio, admin_cliente_ou_master_obrigatorio


@main.route("/admin")
@login_obrigatorio
@admin_cliente_ou_master_obrigatorio
def admin_painel():
    usuario_logado = obter_usuario_logado()

    return render_template(
        "admin_painel.html",
        usuario_logado=usuario_logado,
    )