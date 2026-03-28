from flask import flash, redirect, render_template, request, url_for

from .base import main
from .. import db
from ..helpers.decorators import login_obrigatorio, admin_obrigatorio
from ..models import Cliente


@main.route("/admin/clientes", methods=["GET", "POST"])
@login_obrigatorio
@admin_obrigatorio
def admin_clientes():
    if request.method == "POST":
        nome = (request.form.get("nome") or "").strip()
        documento = (request.form.get("documento") or "").strip() or None
        email = (request.form.get("email") or "").strip().lower() or None
        telefone = (request.form.get("telefone") or "").strip() or None

        if not nome:
            flash("O nome do cliente é obrigatório.", "error")
            return redirect(url_for("main.admin_clientes"))

        cliente = Cliente(
            nome=nome,
            documento=documento,
            email=email,
            telefone=telefone,
            ativo=True,
        )

        db.session.add(cliente)
        db.session.commit()

        flash("Cliente cadastrado com sucesso.", "success")
        return redirect(url_for("main.admin_clientes"))

    clientes = Cliente.query.order_by(Cliente.id.desc()).all()

    return render_template("admin_clientes.html", clientes=clientes)


@main.route("/admin/clientes/<int:cliente_id>/editar", methods=["GET", "POST"])
@login_obrigatorio
@admin_obrigatorio
def admin_editar_cliente(cliente_id):
    cliente = Cliente.query.get_or_404(cliente_id)

    if request.method == "POST":
        nome = (request.form.get("nome") or "").strip()
        documento = (request.form.get("documento") or "").strip() or None
        email = (request.form.get("email") or "").strip().lower() or None
        telefone = (request.form.get("telefone") or "").strip() or None

        if not nome:
            flash("O nome do cliente é obrigatório.", "error")
            return redirect(request.url)

        cliente.nome = nome
        cliente.documento = documento
        cliente.email = email
        cliente.telefone = telefone

        db.session.commit()

        flash("Cliente atualizado com sucesso.", "success")
        return redirect(url_for("main.admin_clientes"))

    return render_template("admin_cliente_editar.html", cliente=cliente)


@main.route("/admin/clientes/<int:cliente_id>/toggle")
@login_obrigatorio
@admin_obrigatorio
def admin_toggle_cliente(cliente_id):
    cliente = Cliente.query.get_or_404(cliente_id)

    cliente.ativo = not cliente.ativo
    db.session.commit()

    if cliente.ativo:
        flash("Cliente ativado com sucesso.", "success")
    else:
        flash("Cliente inativado com sucesso.", "success")

    return redirect(url_for("main.admin_clientes"))