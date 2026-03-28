from functools import wraps

from flask import flash, redirect, url_for

from .auth import obter_usuario_logado
from .permissoes import (
    usuario_tem_acesso_animal,
    usuario_tem_acesso_propriedade,
    usuario_eh_admin_master,
    usuario_eh_admin_cliente,
)
from ..models import Animal, Atendimento, Propriedade


def login_obrigatorio(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        usuario = obter_usuario_logado()

        if not usuario:
            flash("Faça login para acessar o sistema.", "error")
            return redirect(url_for("main.login"))

        return f(*args, **kwargs)

    return decorated_function


def admin_obrigatorio(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        usuario = obter_usuario_logado()

        if not usuario or not usuario_eh_admin_master(usuario):
            flash("Acesso restrito ao administrador principal.", "error")
            return redirect(url_for("main.painel"))

        return f(*args, **kwargs)

    return decorated_function


def admin_cliente_ou_master_obrigatorio(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        usuario = obter_usuario_logado()

        if not usuario:
            flash("Faça login para acessar o sistema.", "error")
            return redirect(url_for("main.login"))

        if not (usuario_eh_admin_master(usuario) or usuario_eh_admin_cliente(usuario)):
            flash("Acesso restrito à administração.", "error")
            return redirect(url_for("main.painel"))

        return f(*args, **kwargs)

    return decorated_function


def acesso_propriedade(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        usuario = obter_usuario_logado()
        propriedade_id = kwargs.get("propriedade_id")

        if not propriedade_id:
            flash("Propriedade não informada.", "error")
            return redirect(url_for("main.painel"))

        propriedade = Propriedade.query.get_or_404(propriedade_id)

        if not usuario_tem_acesso_propriedade(usuario, propriedade):
            flash("Você não tem acesso a essa propriedade.", "error")
            return redirect(url_for("main.propriedades"))

        return f(*args, **kwargs)

    return decorated_function


def acesso_animal(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        usuario = obter_usuario_logado()
        animal_id = kwargs.get("animal_id")

        if not animal_id:
            flash("Animal não informado.", "error")
            return redirect(url_for("main.painel"))

        animal = Animal.query.get_or_404(animal_id)

        if not usuario_tem_acesso_animal(usuario, animal):
            flash("Você não tem acesso a esse animal.", "error")
            return redirect(url_for("main.propriedades"))

        return f(*args, **kwargs)

    return decorated_function


def acesso_atendimento(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        usuario = obter_usuario_logado()
        atendimento_id = kwargs.get("id")

        if not atendimento_id:
            flash("Atendimento não informado.", "error")
            return redirect(url_for("main.painel"))

        atendimento = Atendimento.query.get_or_404(atendimento_id)
        animal = Animal.query.get_or_404(atendimento.animal_id)

        if not usuario_tem_acesso_animal(usuario, animal):
            flash("Você não tem acesso a esse atendimento.", "error")
            return redirect(url_for("main.propriedades"))

        return f(*args, **kwargs)

    return decorated_function