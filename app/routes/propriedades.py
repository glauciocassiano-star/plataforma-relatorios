from flask import flash, redirect, render_template, request, url_for

from .base import main
from .. import db
from ..helpers.auth import obter_usuario_logado
from ..helpers.decorators import login_obrigatorio, acesso_propriedade
from ..helpers.permissoes import usuario_eh_admin_master
from ..models import Animal, Cliente, Propriedade, UsuarioPropriedade
from ..services.propriedade_service import listar_propriedades_do_usuario


@main.route("/propriedades", methods=["GET", "POST"])
@login_obrigatorio
def propriedades():
    usuario = obter_usuario_logado()

    if not usuario:
        flash("Usuário não autenticado.", "error")
        return redirect(url_for("main.login"))

    if request.method == "POST":
        nome = (request.form.get("nome") or "").strip()
        produtor = (request.form.get("produtor") or "").strip()
        cidade = (request.form.get("cidade") or "").strip()
        estado = (request.form.get("estado") or "").strip().upper()

        if not nome or not produtor:
            flash("Nome e produtor são obrigatórios.", "error")
            return redirect(url_for("main.propriedades"))

        cliente_id = None

        if usuario_eh_admin_master(usuario):
            cliente_id_raw = (request.form.get("cliente_id") or "").strip()

            if not cliente_id_raw:
                flash("Selecione o cliente da propriedade.", "error")
                return redirect(url_for("main.propriedades"))

            try:
                cliente_id = int(cliente_id_raw)
            except ValueError:
                flash("Cliente inválido.", "error")
                return redirect(url_for("main.propriedades"))

            cliente = db.session.get(Cliente, cliente_id)
            if not cliente or not cliente.ativo:
                flash("Cliente inválido ou inativo.", "error")
                return redirect(url_for("main.propriedades"))

        else:
            if not usuario.cliente_id or not usuario.cliente or not usuario.cliente.ativo:
                flash("Seu usuário não está vinculado a um cliente ativo.", "error")
                return redirect(url_for("main.propriedades"))

            cliente_id = usuario.cliente_id

        prop = Propriedade(
            nome=nome,
            produtor=produtor,
            cidade=cidade or None,
            estado=estado or None,
            cliente_id=cliente_id,
        )
        db.session.add(prop)
        db.session.flush()

        if not usuario_eh_admin_master(usuario):
            vinculo = UsuarioPropriedade(
                usuario_id=usuario.id,
                propriedade_id=prop.id,
            )
            db.session.add(vinculo)

        db.session.commit()

        flash("Propriedade criada com sucesso!", "success")
        return redirect(url_for("main.propriedades"))

    propriedades = listar_propriedades_do_usuario(usuario)

    clientes = []
    if usuario_eh_admin_master(usuario):
        clientes = (
            Cliente.query
            .filter_by(ativo=True)
            .order_by(Cliente.nome.asc())
            .all()
        )

    return render_template(
        "propriedades.html",
        propriedades=propriedades,
        clientes=clientes,
    )


@main.route("/propriedades/<int:propriedade_id>/excluir")
@login_obrigatorio
@acesso_propriedade
def excluir_propriedade(propriedade_id):
    propriedade = Propriedade.query.get_or_404(propriedade_id)

    animais = Animal.query.filter_by(propriedade_id=propriedade.id).count()

    if animais > 0:
        flash(
            "Não é possível excluir a propriedade porque existem animais cadastrados nela.",
            "error",
        )
        return redirect(url_for("main.propriedades"))

    UsuarioPropriedade.query.filter_by(propriedade_id=propriedade.id).delete()

    db.session.delete(propriedade)
    db.session.commit()

    flash("Propriedade excluída com sucesso.", "success")
    return redirect(url_for("main.propriedades"))