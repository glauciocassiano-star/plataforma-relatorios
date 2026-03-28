from datetime import datetime

from flask import Response, flash, redirect, render_template, request, url_for
from sqlalchemy import and_, func
from weasyprint import HTML

from .base import main
from .. import db
from ..helpers.uploads import salvar_arquivo_exame, arquivo_exame_permitido
from ..helpers.auth import obter_usuario_logado
from ..helpers.decorators import (
    login_obrigatorio,
    acesso_animal,
    acesso_atendimento,
)
from ..models import (
    Animal,
    Atendimento,
    CampoFormulario,
    Formulario,
    Exame,
    ConfiguracaoSistema,
)
from ..services.animal_service import listar_animais_da_propriedade
from ..services.propriedade_service import listar_propriedades_do_usuario
from ..services.atendimento_service import (
    processar_dados_formulario,
    processar_data_atendimento,
    processar_imagens_atendimento,
)


@main.route("/animais/<int:animal_id>/atendimentos/novo", methods=["GET", "POST"])
@login_obrigatorio
@acesso_animal
def novo_atendimento(animal_id: int):
    usuario = obter_usuario_logado()
    animal = Animal.query.get_or_404(animal_id)

    perfil = (usuario.perfil or "tecnico").strip()

    # Apenas admin_master pode simular outro perfil pela query string
    if perfil == "admin_master":
        perfil = (request.args.get("perfil") or "veterinario").strip()

    formulario = (
        Formulario.query
        .filter(Formulario.ativo.is_(True))
        .filter(Formulario.perfil_alvo.in_([perfil, "ambos"]))
        .order_by(Formulario.id.desc())
        .first()
    )

    if not formulario:
        flash(
            f"Não existe formulário ativo para o perfil '{perfil}'. Crie em /admin/formularios.",
            "error",
        )
        return redirect(url_for("main.painel"))

    campos = (
        CampoFormulario.query
        .filter_by(formulario_id=formulario.id)
        .order_by(CampoFormulario.ordem.asc(), CampoFormulario.id.asc())
        .all()
    )

    if not campos:
        flash(
            f"O formulário ativo para o perfil '{perfil}' não possui campos cadastrados. Verifique em /admin/formularios.",
            "error",
        )
        return redirect(url_for("main.painel"))

    if request.method == "POST":
        try:
            dados = processar_dados_formulario(campos, request.form)
            data_atendimento = processar_data_atendimento(request.form)
        except ValueError as e:
            flash(str(e), "error")
            return redirect(request.url)

        atendimento_existente = Atendimento.query.filter_by(
            animal_id=animal.id,
            data_atendimento=data_atendimento,
        ).first()

        duplicado_mesma_data = atendimento_existente is not None

        at = Atendimento(
            animal_id=animal.id,
            tecnico_id=usuario.id,
            formulario_id=formulario.id,
            dados=dados,
            data_atendimento=data_atendimento,
        )
        db.session.add(at)
        db.session.commit()

        arquivos_imagens = request.files.getlist("imagens")
        erros_upload = processar_imagens_atendimento(arquivos_imagens, at.id)
        db.session.commit()

        for erro in erros_upload:
            flash(erro, "error")

        if duplicado_mesma_data:
            flash(
                "Atendimento salvo, mas atenção: já existia outro atendimento para este animal nesta mesma data.",
                "error",
            )
        else:
            flash("Atendimento salvo com sucesso!", "success")

        return redirect(url_for("main.prontuario_animal", animal_id=animal.id))

    return render_template(
        "atendimento_novo.html",
        animal=animal,
        formulario=formulario,
        campos=campos,
        atendimento=None,
        modo_edicao=False,
    )


@main.route("/atendimentos/novo", methods=["GET"])
@login_obrigatorio
def selecionar_atendimento():
    usuario = obter_usuario_logado()

    propriedades = listar_propriedades_do_usuario(usuario)
    propriedade_id = request.args.get("propriedade_id", type=int)
    animais_info = []

    if propriedade_id:
        propriedades_ids = [p.id for p in propriedades]

        if propriedade_id not in propriedades_ids:
            flash("Você não tem acesso a essa propriedade.", "error")
            return redirect(url_for("main.propriedades"))

        animais = listar_animais_da_propriedade(propriedade_id)
        animal_ids = [a.id for a in animais]

        ultimos_atendimentos_por_animal = {}

        if animal_ids:
            subquery = (
                db.session.query(
                    Atendimento.animal_id.label("animal_id"),
                    func.max(Atendimento.data_atendimento).label("max_data")
                )
                .filter(Atendimento.animal_id.in_(animal_ids))
                .group_by(Atendimento.animal_id)
                .subquery()
            )

            ultimos_atendimentos = (
                db.session.query(Atendimento)
                .join(
                    subquery,
                    and_(
                        Atendimento.animal_id == subquery.c.animal_id,
                        Atendimento.data_atendimento == subquery.c.max_data
                    )
                )
                .all()
            )

            ultimos_atendimentos_por_animal = {
                at.animal_id: at for at in ultimos_atendimentos
            }

        animais_info = [
            {
                "animal": animal,
                "ultimo_atendimento": ultimos_atendimentos_por_animal.get(animal.id)
            }
            for animal in animais
        ]

    return render_template(
        "atendimento_selecionar.html",
        propriedades=propriedades,
        animais_info=animais_info,
        propriedade_id=propriedade_id,
    )


@main.route("/atendimento/<int:id>/editar", methods=["GET", "POST"])
@login_obrigatorio
@acesso_atendimento
def editar_atendimento(id):
    atendimento = Atendimento.query.get_or_404(id)
    animal = Animal.query.get_or_404(atendimento.animal_id)

    if atendimento.bloqueado_em:
        flash("Este atendimento está bloqueado e não pode ser editado.", "error")
        return redirect(url_for("main.prontuario_animal", animal_id=animal.id))

    formulario = Formulario.query.get_or_404(atendimento.formulario_id)

    campos = (
        CampoFormulario.query
        .filter_by(formulario_id=formulario.id)
        .order_by(CampoFormulario.ordem.asc(), CampoFormulario.id.asc())
        .all()
    )

    if request.method == "POST":
        try:
            dados = processar_dados_formulario(campos, request.form)
            data_atendimento = processar_data_atendimento(request.form)
        except ValueError as e:
            flash(str(e), "error")
            return redirect(request.url)

        atendimento.data_atendimento = data_atendimento
        atendimento.dados = dados

        db.session.commit()

        arquivos_imagens = request.files.getlist("imagens")
        erros_upload = processar_imagens_atendimento(arquivos_imagens, atendimento.id)
        db.session.commit()

        for erro in erros_upload:
            flash(erro, "error")

        flash("Atendimento atualizado com sucesso!", "success")
        return redirect(url_for("main.prontuario_animal", animal_id=animal.id))

    return render_template(
        "atendimento_novo.html",
        animal=animal,
        formulario=formulario,
        campos=campos,
        atendimento=atendimento,
        modo_edicao=True,
    )


@main.route("/atendimento/<int:id>/excluir")
@login_obrigatorio
@acesso_atendimento
def excluir_atendimento(id):
    usuario = obter_usuario_logado()

    if usuario.perfil not in ["admin_master", "veterinario"]:
        flash("Você não tem permissão para excluir atendimentos.", "error")
        return redirect(url_for("main.painel"))

    atendimento = Atendimento.query.get_or_404(id)
    animal_id = atendimento.animal_id

    db.session.delete(atendimento)
    db.session.commit()

    flash("Atendimento excluído com sucesso.", "success")
    return redirect(url_for("main.prontuario_animal", animal_id=animal_id))


@main.route("/atendimento/<int:id>/bloquear")
@login_obrigatorio
@acesso_atendimento
def bloquear_atendimento(id):
    usuario = obter_usuario_logado()

    if usuario.perfil not in ["admin_master", "veterinario"]:
        flash("Você não tem permissão para bloquear atendimentos.", "error")
        return redirect(url_for("main.painel"))

    atendimento = Atendimento.query.get_or_404(id)

    if atendimento.bloqueado_em:
        flash("Atendimento já está bloqueado.", "error")
        return redirect(url_for("main.prontuario_animal", animal_id=atendimento.animal_id))

    atendimento.bloqueado_em = datetime.utcnow()

    db.session.commit()

    flash("Atendimento bloqueado com sucesso.", "success")
    return redirect(url_for("main.prontuario_animal", animal_id=atendimento.animal_id))


@main.route("/atendimento/<int:id>/desbloquear")
@login_obrigatorio
@acesso_atendimento
def desbloquear_atendimento(id):
    usuario = obter_usuario_logado()

    if usuario.perfil != "admin_master":
        flash("Somente o administrador principal pode desbloquear atendimentos.", "error")
        return redirect(url_for("main.painel"))

    atendimento = Atendimento.query.get_or_404(id)

    if not atendimento.bloqueado_em:
        flash("Este atendimento não está bloqueado.", "error")
        return redirect(
            url_for("main.prontuario_animal", animal_id=atendimento.animal_id)
        )

    atendimento.bloqueado_em = None
    db.session.commit()

    flash("Atendimento desbloqueado com sucesso.", "success")
    return redirect(
        url_for("main.prontuario_animal", animal_id=atendimento.animal_id)
    )


@main.route("/atendimento/<int:id>/pdf")
@login_obrigatorio
@acesso_atendimento
def exportar_atendimento_pdf(id):
    atendimento = Atendimento.query.get_or_404(id)
    animal = Animal.query.get_or_404(atendimento.animal_id)
    config_sistema = ConfiguracaoSistema.query.first()

    html = render_template(
        "atendimento_pdf.html",
        atendimento=atendimento,
        animal=animal,
        config_sistema=config_sistema,
        gerado_em=datetime.now(),
    )

    pdf = HTML(string=html).write_pdf()

    return Response(
        pdf,
        mimetype="application/pdf",
        headers={
            "Content-Disposition": f"inline; filename=atendimento_{atendimento.id}.pdf"
        }
    )


@main.route("/atendimento/<int:id>/exames/novo", methods=["GET", "POST"])
@login_obrigatorio
@acesso_atendimento
def novo_exame(id):
    atendimento = Atendimento.query.get_or_404(id)
    animal = Animal.query.get_or_404(atendimento.animal_id)

    if request.method == "POST":
        categoria = (request.form.get("categoria") or "").strip()
        nome_exame = (request.form.get("nome_exame") or "").strip()
        data_exame_str = (request.form.get("data_exame") or "").strip()
        resultado = (request.form.get("resultado") or "").strip()
        observacoes = (request.form.get("observacoes") or "").strip()

        if categoria not in ["laboratorial", "imagem"]:
            flash("Categoria de exame inválida.", "error")
            return redirect(request.url)

        if not nome_exame:
            flash("O nome do exame é obrigatório.", "error")
            return redirect(request.url)

        data_exame = None
        if data_exame_str:
            try:
                data_exame = datetime.strptime(data_exame_str, "%Y-%m-%d").date()
            except ValueError:
                flash("Data do exame inválida.", "error")
                return redirect(request.url)

        arquivo = request.files.get("arquivo")
        caminho_arquivo = None

        if arquivo and arquivo.filename:
            if not arquivo_exame_permitido(arquivo.filename):
                flash("Arquivo de exame inválido. Envie PDF, PNG, JPG, JPEG ou WEBP.", "error")
                return redirect(request.url)

            caminho_arquivo = salvar_arquivo_exame(arquivo, atendimento.id)

        exame = Exame(
            atendimento_id=atendimento.id,
            categoria=categoria,
            nome_exame=nome_exame,
            data_exame=data_exame,
            resultado=resultado or None,
            observacoes=observacoes or None,
            arquivo=caminho_arquivo,
        )

        db.session.add(exame)
        db.session.commit()

        flash("Exame registrado com sucesso.", "success")
        return redirect(url_for("main.prontuario_animal", animal_id=animal.id))

    return render_template(
        "exame_novo.html",
        atendimento=atendimento,
        animal=animal,
    )