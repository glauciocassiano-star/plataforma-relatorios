from flask import flash, redirect, render_template, request, url_for

from .base import main
from .. import db
from ..helpers.auth import obter_usuario_logado
from ..models import Atendimento, Propriedade, Usuario, UsuarioPropriedade


@main.route("/admin/usuarios", methods=["GET", "POST"])
def admin_usuarios():
    usuario = obter_usuario_logado()
    if not usuario or usuario.perfil != "admin":
        flash("Acesso restrito ao admin.", "error")
        return redirect(url_for("main.painel"))

    if request.method == "POST":
        nome = (request.form.get("nome") or "").strip()
        email = (request.form.get("email") or "").strip().lower()
        senha = (request.form.get("senha") or "").strip()
        perfil = (request.form.get("perfil") or "tecnico").strip()

        if not nome or not email or not senha:
            flash("Nome, email e senha são obrigatórios.", "error")
            return redirect(request.url)

        usuario_existente = Usuario.query.filter_by(email=email).first()
        if usuario_existente:
            flash("Já existe um usuário com esse email.", "error")
            return redirect(request.url)

        novo_usuario = Usuario(nome=nome, email=email, perfil=perfil)
        novo_usuario.set_password(senha)

        db.session.add(novo_usuario)
        db.session.commit()

        flash("Usuário criado com sucesso.", "success")
        return redirect(url_for("main.admin_usuarios"))

    usuarios = Usuario.query.order_by(Usuario.id.desc()).all()
    return render_template("admin_usuarios.html", usuarios=usuarios)


@main.route("/admin/usuarios/<int:usuario_id>/propriedades", methods=["GET", "POST"])
def admin_usuario_propriedades(usuario_id):
    usuario_logado = obter_usuario_logado()
    if not usuario_logado or usuario_logado.perfil != "admin":
        flash("Acesso restrito ao admin.", "error")
        return redirect(url_for("main.painel"))

    usuario = Usuario.query.get_or_404(usuario_id)
    propriedades = Propriedade.query.order_by(Propriedade.nome.asc()).all()

    if request.method == "POST":
        selecionadas = request.form.getlist("propriedades")

        UsuarioPropriedade.query.filter_by(usuario_id=usuario.id).delete()

        for prop_id in selecionadas:
            vinculo = UsuarioPropriedade(
                usuario_id=usuario.id,
                propriedade_id=int(prop_id)
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
        vinculadas=vinculadas
    )


@main.route("/admin/usuarios/<int:usuario_id>/editar", methods=["GET", "POST"])
def admin_editar_usuario(usuario_id):
    usuario_logado = obter_usuario_logado()
    if not usuario_logado or usuario_logado.perfil != "admin":
        flash("Acesso restrito ao admin.", "error")
        return redirect(url_for("main.painel"))

    usuario = Usuario.query.get_or_404(usuario_id)

    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        perfil = (request.form.get("perfil") or "tecnico").strip()
        senha = (request.form.get("senha") or "").strip()

        if not email:
            flash("Email é obrigatório.", "error")
            return redirect(request.url)

        usuario_existente = Usuario.query.filter(
            Usuario.email == email,
            Usuario.id != usuario.id
        ).first()

        if usuario_existente:
            flash("Já existe outro usuário com esse email.", "error")
            return redirect(request.url)

        usuario.email = email
        usuario.perfil = perfil

        if senha:
            usuario.set_password(senha)

        db.session.commit()

        flash("Usuário atualizado com sucesso.", "success")
        return redirect(url_for("main.admin_usuarios"))

    return render_template("admin_usuario_editar.html", usuario=usuario)


@main.route("/admin/usuarios/<int:usuario_id>/excluir")
def admin_excluir_usuario(usuario_id):
    usuario_logado = obter_usuario_logado()
    if not usuario_logado or usuario_logado.perfil != "admin":
        flash("Acesso restrito ao admin.", "error")
        return redirect(url_for("main.painel"))

    usuario = Usuario.query.get_or_404(usuario_id)

    if usuario.id == usuario_logado.id:
        flash("Você não pode excluir seu próprio usuário.", "error")
        return redirect(url_for("main.admin_usuarios"))

    atendimentos = Atendimento.query.filter_by(tecnico_id=usuario.id).count()
    if atendimentos > 0:
        flash("Não é possível excluir este usuário porque existem atendimentos vinculados.", "error")
        return redirect(url_for("main.admin_usuarios"))

    UsuarioPropriedade.query.filter_by(usuario_id=usuario.id).delete()

    db.session.delete(usuario)
    db.session.commit()

    flash("Usuário excluído com sucesso.", "success")
    return redirect(url_for("main.admin_usuarios"))