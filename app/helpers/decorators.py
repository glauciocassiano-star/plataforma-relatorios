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


def _usuario_pode_usar_sistema(usuario):
    if not usuario:
        return False, "Faça login para acessar o sistema."

    if not getattr(usuario, "ativo", True):
        return False, "Seu usuário está inativo. Procure o administrador do sistema."

    if usuario_eh_admin_master(usuario):
        return True, None

    if not getattr(usuario, "cliente", None):
        return False, "Seu usuário não está vinculado a um cliente válido."

    if not getattr(usuario.cliente, "ativo", True):
        return False, "O cliente vinculado ao seu usuário está inativo."

    return True, None


def usuario_pode_acessar_sensor(usuario):
    if not usuario:
        return False

    if getattr(usuario, "perfil", None) in ["admin_master", "admin_cliente"]:
        return True

    return bool(getattr(usuario, "pode_usar_sensor", False))


def login_obrigatorio(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        usuario = obter_usuario_logado()
        permitido, mensagem = _usuario_pode_usar_sistema(usuario)

        if not permitido:
            flash(mensagem, "error")
            return redirect(url_for("main.login"))

        return f(*args, **kwargs)

    return decorated_function


def admin_obrigatorio(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        usuario = obter_usuario_logado()
        permitido, mensagem = _usuario_pode_usar_sistema(usuario)

        if not permitido:
            flash(mensagem, "error")
            return redirect(url_for("main.login"))

        if not usuario_eh_admin_master(usuario):
            flash("Acesso restrito ao administrador principal.", "error")
            return redirect(url_for("main.painel"))

        return f(*args, **kwargs)

    return decorated_function


def admin_cliente_ou_master_obrigatorio(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        usuario = obter_usuario_logado()
        permitido, mensagem = _usuario_pode_usar_sistema(usuario)

        if not permitido:
            flash(mensagem, "error")
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
        permitido, mensagem = _usuario_pode_usar_sistema(usuario)

        if not permitido:
            flash(mensagem, "error")
            return redirect(url_for("main.login"))

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
        permitido, mensagem = _usuario_pode_usar_sistema(usuario)

        if not permitido:
            flash(mensagem, "error")
            return redirect(url_for("main.login"))

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
        permitido, mensagem = _usuario_pode_usar_sistema(usuario)

        if not permitido:
            flash(mensagem, "error")
            return redirect(url_for("main.login"))

        atendimento_id = kwargs.get("atendimento_id") or kwargs.get("id")

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


def acesso_sensor_obrigatorio(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        usuario = obter_usuario_logado()
        permitido, mensagem = _usuario_pode_usar_sistema(usuario)

        if not permitido:
            flash(mensagem, "error")
            return redirect(url_for("main.login"))

        if not usuario_pode_acessar_sensor(usuario):
            flash("Você não tem permissão para usar o módulo do sensor.", "error")
            return redirect(url_for("main.painel"))

        return f(*args, **kwargs)

    return decorated_function
