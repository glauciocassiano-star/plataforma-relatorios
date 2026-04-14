import re

from flask import flash, redirect, render_template, request, url_for

from .base import main
from .. import db
from ..helpers.auth import obter_usuario_logado
from ..helpers.decorators import admin_cliente_ou_master_obrigatorio
from ..helpers.permissoes import (
    usuario_eh_admin_master,
    usuario_eh_admin_cliente,
    usuario_pode_editar_usuario,
    usuario_pode_excluir_usuario,
    usuario_pode_gerenciar_propriedades_usuario,
)
from ..models import Atendimento, Cliente, Propriedade, Usuario, UsuarioPropriedade


def senha_forte_valida(senha: str) -> bool:
    """
    Regras:
    - mínimo de 6 caracteres
    - pelo menos 1 letra maiúscula
    - sem espaços
    - pelo menos 5 caracteres alfanuméricos no total
    - pelo menos 1 caractere especial
    """
    if not senha:
        return False

    if len(senha) < 6:
        return False

    if any(ch.isspace() for ch in senha):
        return False

    if not re.search(r"[A-Z]", senha):
        return False

    if len(re.findall(r"[A-Za-z0-9]", senha)) < 5:
        return False

    if not re.search(r"[^A-Za-z0-9]", senha):
        return False

    return True


@main.route("/admin/usuarios", methods=["GET", "POST"])
@admin_cliente_ou_master_obrigatorio
def admin_usuarios():
    usuario_logado = obter_usuario_logado()

    if request.method == "POST":
        nome = (request.form.get("nome") or "").strip()
        email = (request.form.get("email") or "").strip().lower()
        senha = (request.form.get("senha") or "").strip()
        perfil = (request.form.get("perfil") or "tecnico").strip()
        pode_usar_sensor = True if request.form.get("pode_usar_sensor") else False

        if not nome or not email or not senha:
            flash("Nome, email e senha são obrigatórios.", "error")
            return redirect(request.url)

        if not senha_forte_valida(senha):
            flash(
                "A senha deve ter no mínimo 6 caracteres, ao menos 1 letra maiúscula, "
                "sem espaços, pelo menos 5 letras ou números e 1 caractere especial.",
                "error",
            )
            return redirect(request.url)

        if usuario_eh_admin_cliente(usuario_logado):
            if perfil not in ["tecnico", "veterinario"]:
                flash(
                    "Você só pode criar usuários com perfil técnico ou veterinário.",
                    "error",
                )
                return redirect(request.url)

        usuario_existente = Usuario.query.filter_by(email=email).first()
        if usuario_existente:
            flash("Já existe um usuário com esse email.", "error")
            return redirect(request.url)

        if usuario_eh_admin_master(usuario_logado):
            cliente_id_raw = request.form.get("cliente_id", "").strip()
            if perfil == "admin_master":
                cliente_id = None
            else:
                if not cliente_id_raw:
                    flash("Selecione o cliente do usuário.", "error")
                    return redirect(request.url)

                try:
                    cliente_id = int(cliente_id_raw)
                except ValueError:
                    flash("Cliente inválido.", "error")
                    return redirect(request.url)

                cliente = db.session.get(Cliente, cliente_id)
                if not cliente or not cliente.ativo:
                    flash("Cliente inválido ou inativo.", "error")
                    return redirect(request.url)

            criado_por_id = None
        else:
            if not usuario_logado.cliente_id or not usuario_logado.cliente:
                flash("Seu usuário não está vinculado a um cliente válido.", "error")
                return redirect(request.url)

            if not usuario_logado.cliente.ativo:
                flash("O cliente vinculado ao seu usuário está inativo.", "error")
                return redirect(request.url)

            cliente_id = usuario_logado.cliente_id
            criado_por_id = usuario_logado.id

        novo_usuario = Usuario(
            nome=nome,
            email=email,
            perfil=perfil,
            cliente_id=cliente_id,
            ativo=True,
            pode_usar_sensor=pode_usar_sensor,
            criado_por_id=criado_por_id,
        )
        novo_usuario.set_password(senha)

        db.session.add(novo_usuario)
        db.session.commit()

        flash("Usuário criado com sucesso.", "success")
        return redirect(url_for("main.admin_usuarios"))

    if usuario_eh_admin_master(usuario_logado):
        usuarios = Usuario.query.order_by(Usuario.id.desc()).all()
        clientes = (
            Cliente.query
            .filter_by(ativo=True)
            .order_by(Cliente.nome.asc())
            .all()
        )
    else:
        usuarios = (
            Usuario.query
            .filter(
                Usuario.cliente_id == usuario_logado.cliente_id,
                Usuario.perfil.in_(["tecnico", "veterinario"]),
                Usuario.criado_por_id == usuario_logado.id,
            )
            .order_by(Usuario.id.desc())
            .all()
        )
        clientes = []

    return render_template(
        "admin_usuarios.html",
        usuarios=usuarios,
        clientes=clientes,
        usuario_logado=usuario_logado,
    )


@main.route("/admin/usuarios/<int:usuario_id>/propriedades", methods=["GET", "POST"])
@admin_cliente_ou_master_obrigatorio
def admin_usuario_propriedades(usuario_id):
    usuario_logado = obter_usuario_logado()
    usuario = db.session.get(Usuario, usuario_id)

    if not usuario:
        flash("Usuário não encontrado.", "error")
        return redirect(url_for("main.admin_usuarios"))

    if not usuario_pode_gerenciar_propriedades_usuario(usuario_logado, usuario):
        flash("Você não tem permissão para gerenciar propriedades desse usuário.", "error")
        return redirect(url_for("main.admin_usuarios"))

    if usuario_eh_admin_master(usuario_logado):
        propriedades = (
            Propriedade.query
            .filter(Propriedade.cliente_id == usuario.cliente_id)
            .order_by(Propriedade.nome.asc())
            .all()
        )
    else:
        propriedades = (
            Propriedade.query
            .join(
                UsuarioPropriedade,
                UsuarioPropriedade.propriedade_id == Propriedade.id,
            )
            .filter(
                UsuarioPropriedade.usuario_id == usuario_logado.id,
                Propriedade.cliente_id == usuario_logado.cliente_id,
            )
            .order_by(Propriedade.nome.asc())
            .all()
        )

    if request.method == "POST":
        selecionadas = request.form.getlist("propriedades")

        UsuarioPropriedade.query.filter_by(usuario_id=usuario.id).delete()

        for prop_id in selecionadas:
            try:
                prop_id_int = int(prop_id)
            except (TypeError, ValueError):
                continue

            prop = db.session.get(Propriedade, prop_id_int)
            if not prop:
                continue

            if prop.cliente_id != usuario.cliente_id:
                continue

            if usuario_eh_admin_cliente(usuario_logado):
                vinculo_admin = UsuarioPropriedade.query.filter_by(
                    usuario_id=usuario_logado.id,
                    propriedade_id=prop.id,
                ).first()

                if not vinculo_admin:
                    continue

            vinculo = UsuarioPropriedade(
                usuario_id=usuario.id,
                propriedade_id=prop.id,
            )
            db.session.add(vinculo)

        db.session.commit()

        flash("Vínculos atualizados com sucesso.", "success")
        return redirect(url_for("main.admin_usuarios"))

    vinculadas = {
        v.propriedade_id
        for v in UsuarioPropriedade.query.filter_by(usuario_id=usuario.id).all()
    }

    return render_template(
        "admin_usuario_propriedades.html",
        usuario=usuario,
        propriedades=propriedades,
        vinculadas=vinculadas,
    )


@main.route("/admin/usuarios/<int:usuario_id>/editar", methods=["GET", "POST"])
@admin_cliente_ou_master_obrigatorio
def admin_editar_usuario(usuario_id):
    usuario_logado = obter_usuario_logado()
    usuario = db.session.get(Usuario, usuario_id)

    if not usuario:
        flash("Usuário não encontrado.", "error")
        return redirect(url_for("main.admin_usuarios"))

    if not usuario_pode_editar_usuario(usuario_logado, usuario):
        flash("Você não tem permissão para editar esse usuário.", "error")
        return redirect(url_for("main.admin_usuarios"))

    if request.method == "POST":
        nome = (request.form.get("nome") or "").strip()
        email = (request.form.get("email") or "").strip().lower()
        perfil = (request.form.get("perfil") or "tecnico").strip()
        senha = (request.form.get("senha") or "").strip()
        pode_usar_sensor = True if request.form.get("pode_usar_sensor") else False

        if not nome or not email:
            flash("Nome e email são obrigatórios.", "error")
            return redirect(request.url)

        if usuario_eh_admin_cliente(usuario_logado):
            if perfil not in ["tecnico", "veterinario"]:
                flash("Você só pode definir perfis técnico ou veterinário.", "error")
                return redirect(request.url)

        usuario_existente = Usuario.query.filter(
            Usuario.email == email,
            Usuario.id != usuario.id,
        ).first()

        if usuario_existente:
            flash("Já existe outro usuário com esse email.", "error")
            return redirect(request.url)

        usuario.nome = nome
        usuario.email = email
        usuario.perfil = perfil
        usuario.pode_usar_sensor = pode_usar_sensor

        if usuario_eh_admin_master(usuario_logado):
            cliente_id_raw = (request.form.get("cliente_id") or "").strip()
            if perfil == "admin_master":
                if usuario.cliente_id is not None:
                    usuario.cliente_id = None
                    usuario.criado_por_id = None
                    UsuarioPropriedade.query.filter_by(usuario_id=usuario.id).delete()
            else:
                if not cliente_id_raw:
                    flash("Selecione o cliente do usuário.", "error")
                    return redirect(request.url)

                try:
                    cliente_id = int(cliente_id_raw)
                except ValueError:
                    flash("Cliente inválido.", "error")
                    return redirect(request.url)

                cliente = db.session.get(Cliente, cliente_id)
                if not cliente or not cliente.ativo:
                    flash("Cliente inválido ou inativo.", "error")
                    return redirect(request.url)

                if usuario.cliente_id != cliente.id:
                    usuario.cliente_id = cliente.id
                    usuario.criado_por_id = None
                    UsuarioPropriedade.query.filter_by(usuario_id=usuario.id).delete()

        if senha:
            if not senha_forte_valida(senha):
                flash(
                    "A nova senha deve ter no mínimo 6 caracteres, ao menos 1 letra maiúscula, "
                    "sem espaços, pelo menos 5 letras ou números e 1 caractere especial.",
                    "error",
                )
                return redirect(request.url)

            usuario.set_password(senha)

        db.session.commit()

        flash("Usuário atualizado com sucesso.", "success")
        return redirect(url_for("main.admin_usuarios"))

    clientes = []
    if usuario_eh_admin_master(usuario_logado):
        clientes = (
            Cliente.query
            .filter_by(ativo=True)
            .order_by(Cliente.nome.asc())
            .all()
        )

    return render_template(
        "admin_usuario_editar.html",
        usuario=usuario,
        clientes=clientes,
        usuario_logado=usuario_logado,
    )


@main.route("/admin/usuarios/<int:usuario_id>/excluir")
@admin_cliente_ou_master_obrigatorio
def admin_excluir_usuario(usuario_id):
    usuario_logado = obter_usuario_logado()
    usuario = db.session.get(Usuario, usuario_id)

    if not usuario:
        flash("Usuário não encontrado.", "error")
        return redirect(url_for("main.admin_usuarios"))

    if usuario.id == usuario_logado.id:
        flash("Você não pode excluir seu próprio usuário.", "error")
        return redirect(url_for("main.admin_usuarios"))

    if not usuario_pode_excluir_usuario(usuario_logado, usuario):
        flash("Você não tem permissão para excluir esse usuário.", "error")
        return redirect(url_for("main.admin_usuarios"))

    atendimentos = Atendimento.query.filter_by(tecnico_id=usuario.id).count()
    if atendimentos > 0:
        flash(
            "Não é possível excluir este usuário porque existem atendimentos vinculados.",
            "error",
        )
        return redirect(url_for("main.admin_usuarios"))

    UsuarioPropriedade.query.filter_by(usuario_id=usuario.id).delete()

    db.session.delete(usuario)
    db.session.commit()

    flash("Usuário excluído com sucesso.", "success")
    return redirect(url_for("main.admin_usuarios"))
