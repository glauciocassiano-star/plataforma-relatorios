import json

from flask import flash, redirect, render_template, request, url_for

from .base import main
from .. import db
from ..helpers.auth import obter_usuario_logado
from ..helpers.decorators import admin_obrigatorio
from ..models import Atendimento, CampoFormulario, Cliente, Formulario, Usuario
from ..services.formulario_service import (
    clonar_formulario_base,
    formulario_eh_editavel,
    listar_campos_formulario,
    normalizar_contexto,
)


@main.route("/admin/formularios", methods=["GET", "POST"])
@admin_obrigatorio
def admin_formularios():
    if request.method == "POST":
        nome = (request.form.get("nome") or "").strip()
        perfil_alvo = (request.form.get("perfil_alvo") or "tecnico").strip().lower()
        tipo_contexto = normalizar_contexto(request.form.get("tipo_contexto"))
        ativo = True if request.form.get("ativo") else False
        template_base = True if request.form.get("template_base") else False

        cliente_id_raw = (request.form.get("cliente_id") or "").strip()
        cliente_id = int(cliente_id_raw) if cliente_id_raw.isdigit() else None

        if not nome:
            flash("Nome do formulário é obrigatório.", "error")
            return redirect(request.url)

        if template_base:
            cliente_id = None

        formulario = Formulario(
            nome=nome,
            perfil_alvo=perfil_alvo,
            ativo=ativo,
            tipo_contexto=tipo_contexto,
            template_base=template_base,
            cliente_id=cliente_id,
            formulario_origem_id=None,
        )
        db.session.add(formulario)
        db.session.commit()

        flash("Formulário criado com sucesso.", "success")
        return redirect(url_for("main.admin_formularios"))

    formularios = Formulario.query.order_by(Formulario.id.desc()).all()
    clientes = Cliente.query.filter_by(ativo=True).order_by(Cliente.nome.asc()).all()

    formularios_info = []
    for f in formularios:
        total_campos = CampoFormulario.query.filter_by(formulario_id=f.id).count()
        total_atendimentos = Atendimento.query.filter_by(formulario_id=f.id).count()

        formularios_info.append({
            "obj": f,
            "total_campos": total_campos,
            "total_atendimentos": total_atendimentos,
        })

    return render_template(
        "admin_formularios.html",
        formularios_info=formularios_info,
        clientes=clientes,
    )


@main.route("/admin/formularios/clonar", methods=["POST"])
@admin_obrigatorio
def admin_clonar_formulario_base():
    formulario_base_id_raw = (request.form.get("formulario_base_id") or "").strip()
    cliente_id_raw = (request.form.get("cliente_id") or "").strip()
    novo_nome = (request.form.get("novo_nome") or "").strip()

    if not formulario_base_id_raw.isdigit():
        flash("Modelo base inválido.", "error")
        return redirect(url_for("main.admin_formularios"))

    if not cliente_id_raw.isdigit():
        flash("Cliente inválido.", "error")
        return redirect(url_for("main.admin_formularios"))

    formulario_base_id = int(formulario_base_id_raw)
    cliente_id = int(cliente_id_raw)

    formulario_base = Formulario.query.get_or_404(formulario_base_id)

    if not formulario_base.template_base:
        flash("Apenas modelos base podem ser clonados.", "error")
        return redirect(url_for("main.admin_formularios"))

    novo_formulario = clonar_formulario_base(
        formulario_base_id=formulario_base_id,
        cliente_id=cliente_id,
        novo_nome=novo_nome or None,
        ativo=True,
    )

    flash("Formulário clonado com sucesso para o cliente.", "success")
    return redirect(url_for("main.admin_formulario_campos", formulario_id=novo_formulario.id))


@main.route("/admin/formularios/<int:formulario_id>/excluir")
@admin_obrigatorio
def admin_excluir_formulario(formulario_id):
    formulario = Formulario.query.get_or_404(formulario_id)
    usuario = obter_usuario_logado()

    if not usuario:
        flash("Usuário não autenticado.", "error")
        return redirect(url_for("main.login"))

    eh_admin_master = getattr(usuario, "perfil", None) == "admin_master"

    # Apenas admin_master pode excluir template-base
    if formulario.template_base and not eh_admin_master:
        flash("Modelos base do sistema não podem ser excluídos.", "error")
        return redirect(url_for("main.admin_formularios"))

    atendimentos = Atendimento.query.filter_by(formulario_id=formulario.id).all()

    # Para usuários que não são admin_master, mantém a proteção extra
    if not eh_admin_master:
        pode_excluir = True

        for at in atendimentos:
            usuario_atendimento = Usuario.query.get(at.tecnico_id)
            if usuario_atendimento and usuario_atendimento.perfil not in [
                "admin",
                "admin_master",
                "admin_cliente",
            ]:
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
        if not formulario_eh_editavel(formulario):
            flash("O modelo base não deve ser editado diretamente. Clone-o para um cliente.", "error")
            return redirect(request.url)

        rotulo = (request.form.get("rotulo") or "").strip()
        nome_chave = (request.form.get("nome_chave") or "").strip()
        tipo = (request.form.get("tipo") or "text").strip()
        obrigatorio = True if request.form.get("obrigatorio") else False
        ordem = (request.form.get("ordem") or "0").strip()
        opcoes_raw = (request.form.get("opcoes") or "").strip()

        grupo = (request.form.get("grupo") or "").strip() or None
        ajuda = (request.form.get("ajuda") or "").strip() or None
        placeholder = (request.form.get("placeholder") or "").strip() or None
        visivel = True if request.form.get("visivel") else False
        editavel = True if request.form.get("editavel") else False

        if not rotulo or not nome_chave:
            flash("Rótulo e nome_chave são obrigatórios.", "error")
            return redirect(request.url)

        try:
            ordem_int = int(ordem) if ordem else 0
        except ValueError:
            ordem_int = 0

        opcoes = None
        if tipo in ["select", "checkbox"]:
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
            grupo=grupo,
            ajuda=ajuda,
            placeholder=placeholder,
            visivel=visivel,
            editavel=editavel,
        )
        db.session.add(campo)
        db.session.commit()

        flash("Campo criado com sucesso.", "success")
        return redirect(url_for("main.admin_formulario_campos", formulario_id=formulario.id))

    campos = listar_campos_formulario(formulario.id)
    return render_template(
        "admin_formulario_campos.html",
        formulario=formulario,
        campos=campos,
    )


@main.route("/admin/campos/<int:campo_id>/editar", methods=["GET", "POST"])
@admin_obrigatorio
def admin_editar_campo(campo_id):
    campo = CampoFormulario.query.get_or_404(campo_id)
    formulario = Formulario.query.get_or_404(campo.formulario_id)

    if not formulario_eh_editavel(formulario):
        flash("O modelo base não deve ser editado diretamente. Clone-o para um cliente.", "error")
        return redirect(url_for("main.admin_formulario_campos", formulario_id=formulario.id))

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

        campo.grupo = (request.form.get("grupo") or "").strip() or None
        campo.ajuda = (request.form.get("ajuda") or "").strip() or None
        campo.placeholder = (request.form.get("placeholder") or "").strip() or None
        campo.visivel = True if request.form.get("visivel") else False
        campo.editavel = True if request.form.get("editavel") else False

        opcoes_raw = (request.form.get("opcoes") or "").strip()

        if campo.tipo in ["select", "checkbox"]:
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
    formulario = Formulario.query.get_or_404(campo.formulario_id)

    if not formulario_eh_editavel(formulario):
        flash("O modelo base não deve ser editado diretamente. Clone-o para um cliente.", "error")
        return redirect(url_for("main.admin_formulario_campos", formulario_id=formulario.id))

    formulario_id = campo.formulario_id

    db.session.delete(campo)
    db.session.commit()

    flash("Campo excluído.", "success")
    return redirect(url_for("main.admin_formulario_campos", formulario_id=formulario_id))