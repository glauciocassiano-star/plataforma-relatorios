import json

from flask import flash, redirect, render_template, request, url_for

from .base import main
from .. import db
from ..helpers.decorators import admin_obrigatorio
from ..models import Atendimento, CampoFormulario, Formulario, Usuario


@main.route("/admin/formularios", methods=["GET", "POST"])
@admin_obrigatorio
def admin_formularios():
    if request.method == "POST":
        nome = (request.form.get("nome") or "").strip()
        perfil_alvo = (request.form.get("perfil_alvo") or "tecnico").strip()
        ativo = True if request.form.get("ativo") else False

        if not nome:
            flash("Nome do formulário é obrigatório.", "error")
            return redirect(request.url)

        f = Formulario(nome=nome, perfil_alvo=perfil_alvo, ativo=ativo)
        db.session.add(f)
        db.session.commit()

        flash("Formulário criado com sucesso.", "success")
        return redirect(url_for("main.admin_formularios"))

    formularios = Formulario.query.order_by(Formulario.id.desc()).all()

    formularios_info = []
    for f in formularios:
        total_campos = CampoFormulario.query.filter_by(formulario_id=f.id).count()
        total_atendimentos = Atendimento.query.filter_by(formulario_id=f.id).count()

        formularios_info.append({
            "obj": f,
            "total_campos": total_campos,
            "total_atendimentos": total_atendimentos,
        })

    return render_template("admin_formularios.html", formularios_info=formularios_info)


@main.route("/admin/formularios/<int:formulario_id>/excluir")
@admin_obrigatorio
def admin_excluir_formulario(formulario_id):
    formulario = Formulario.query.get_or_404(formulario_id)
    atendimentos = Atendimento.query.filter_by(formulario_id=formulario.id).all()

    pode_excluir = True

    for at in atendimentos:
        usuario_atendimento = Usuario.query.get(at.tecnico_id)
        if usuario_atendimento and usuario_atendimento.perfil != "admin":
            pode_excluir = False
            break

    if not pode_excluir:
        flash(
            "Este formulário já foi utilizado por usuários não-admin e não pode ser excluído. Você pode desativá-lo.",
            "error",
        )
        return redirect(url_for("main.admin_formularios"))

    CampoFormulario.query.filter_by(formulario_id=formulario.id).delete()
    Atendimento.query.filter_by(formulario_id=formulario.id).delete()

    db.session.delete(formulario)
    db.session.commit()

    flash("Formulário excluído com sucesso.", "success")
    return redirect(url_for("main.admin_formularios"))


@main.route("/admin/formularios/<int:formulario_id>/toggle_ativo")
@admin_obrigatorio
def admin_toggle_formulario_ativo(formulario_id):
    formulario = Formulario.query.get_or_404(formulario_id)
    total_campos = CampoFormulario.query.filter_by(formulario_id=formulario.id).count()

    if not formulario.ativo and total_campos == 0:
        flash("Não é possível ativar um formulário sem campos cadastrados.", "error")
        return redirect(url_for("main.admin_formularios"))

    formulario.ativo = not formulario.ativo
    db.session.commit()

    if formulario.ativo:
        flash("Formulário ativado com sucesso.", "success")
    else:
        flash("Formulário desativado com sucesso.", "success")

    return redirect(url_for("main.admin_formularios"))


@main.route("/admin/formularios/<int:formulario_id>/campos", methods=["GET", "POST"])
@admin_obrigatorio
def admin_formulario_campos(formulario_id: int):
    formulario = Formulario.query.get_or_404(formulario_id)

    if request.method == "POST":
        rotulo = (request.form.get("rotulo") or "").strip()
        nome_chave = (request.form.get("nome_chave") or "").strip()
        tipo = (request.form.get("tipo") or "text").strip()
        obrigatorio = True if request.form.get("obrigatorio") else False
        ordem = (request.form.get("ordem") or "0").strip()
        opcoes_raw = (request.form.get("opcoes") or "").strip()

        if not rotulo or not nome_chave:
            flash("Rótulo e nome_chave são obrigatórios.", "error")
            return redirect(request.url)

        try:
            ordem_int = int(ordem) if ordem else 0
        except ValueError:
            ordem_int = 0

        opcoes = None
        if tipo == "select":
            if opcoes_raw.startswith("["):
                try:
                    opcoes = json.loads(opcoes_raw)
                except Exception:
                    flash("Opções inválidas. Use JSON válido ou texto separado por vírgula.", "error")
                    return redirect(request.url)
            elif opcoes_raw:
                opcoes = [x.strip() for x in opcoes_raw.split(",") if x.strip()]

        campo = CampoFormulario(
            formulario_id=formulario.id,
            rotulo=rotulo,
            nome_chave=nome_chave,
            tipo=tipo,
            obrigatorio=obrigatorio,
            opcoes=opcoes,
            ordem=ordem_int,
        )
        db.session.add(campo)
        db.session.commit()

        flash("Campo criado com sucesso.", "success")
        return redirect(url_for("main.admin_formulario_campos", formulario_id=formulario.id))

    campos = (
        CampoFormulario.query
        .filter_by(formulario_id=formulario.id)
        .order_by(CampoFormulario.ordem.asc(), CampoFormulario.id.asc())
        .all()
    )
    return render_template("admin_formulario_campos.html", formulario=formulario, campos=campos)


@main.route("/admin/campos/<int:campo_id>/editar", methods=["GET", "POST"])
@admin_obrigatorio
def admin_editar_campo(campo_id):
    campo = CampoFormulario.query.get_or_404(campo_id)
    formulario = Formulario.query.get_or_404(campo.formulario_id)

    if request.method == "POST":
        campo.rotulo = (request.form.get("rotulo") or "").strip()
        campo.nome_chave = (request.form.get("nome_chave") or "").strip()
        campo.tipo = (request.form.get("tipo") or "text").strip()
        campo.obrigatorio = True if request.form.get("obrigatorio") else False

        ordem = (request.form.get("ordem") or "0").strip()

        try:
            campo.ordem = int(ordem)
        except ValueError:
            campo.ordem = 0

        opcoes_raw = (request.form.get("opcoes") or "").strip()

        if campo.tipo == "select":
            if opcoes_raw.startswith("["):
                try:
                    campo.opcoes = json.loads(opcoes_raw)
                except Exception:
                    flash("Opções inválidas.", "error")
                    return redirect(request.url)
            elif opcoes_raw:
                campo.opcoes = [x.strip() for x in opcoes_raw.split(",") if x.strip()]
        else:
            campo.opcoes = None

        db.session.commit()

        flash("Campo atualizado com sucesso.", "success")
        return redirect(url_for("main.admin_formulario_campos", formulario_id=formulario.id))

    return render_template(
        "admin_campo_editar.html",
        campo=campo,
        formulario=formulario
    )


@main.route("/admin/campos/<int:campo_id>/excluir")
@admin_obrigatorio
def admin_excluir_campo(campo_id):
    campo = CampoFormulario.query.get_or_404(campo_id)
    formulario_id = campo.formulario_id

    db.session.delete(campo)
    db.session.commit()

    flash("Campo excluído.", "success")
    return redirect(url_for("main.admin_formulario_campos", formulario_id=formulario_id))