from datetime import datetime

from flask import Blueprint, Response, flash, redirect, render_template, request, session, url_for
from weasyprint import HTML

from .. import db
from ..helpers.decorators import login_obrigatorio
from ..helpers.permissoes import usuario_tem_acesso_propriedade
from ..models import (
    AreaCultivo,
    CicloCultivo,
    ConfiguracaoSistema,
    ManejoAgricola,
    Propriedade,
    Usuario,
)

agricultura_bp = Blueprint("agricultura", __name__, url_prefix="/agricultura")


@agricultura_bp.route("/propriedade/<int:propriedade_id>")
@login_obrigatorio
def painel_agricola(propriedade_id):
    usuario_id = session.get("usuario_id")
    usuario = Usuario.query.get(usuario_id)

    propriedade = Propriedade.query.get_or_404(propriedade_id)

    if not usuario_tem_acesso_propriedade(usuario, propriedade):
        flash("Você não tem permissão para acessar esta propriedade.", "error")
        return redirect(url_for("main.painel"))

    areas = (
        AreaCultivo.query
        .filter_by(propriedade_id=propriedade.id)
        .order_by(AreaCultivo.criado_em.desc())
        .all()
    )

    return render_template(
        "agricultura/painel_agricola.html",
        propriedade=propriedade,
        areas=areas,
    )


@agricultura_bp.route("/propriedade/<int:propriedade_id>/areas/nova", methods=["GET", "POST"])
@login_obrigatorio
def nova_area_cultivo(propriedade_id):
    usuario_id = session.get("usuario_id")
    usuario = Usuario.query.get(usuario_id)

    propriedade = Propriedade.query.get_or_404(propriedade_id)

    if not usuario_tem_acesso_propriedade(usuario, propriedade):
        flash("Você não tem permissão para alterar esta propriedade.", "error")
        return redirect(url_for("main.painel"))

    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        tipo_area = request.form.get("tipo_area", "").strip()
        area_hectares_raw = request.form.get("area_hectares", "").strip()
        observacoes = request.form.get("observacoes", "").strip()
        ativo = request.form.get("ativo") == "on"

        if not nome:
            flash("Informe o nome da área de cultivo.", "error")
            return render_template(
                "agricultura/nova_area_cultivo.html",
                propriedade=propriedade,
            )

        area_existente = AreaCultivo.query.filter_by(
            propriedade_id=propriedade.id,
            nome=nome,
        ).first()

        if area_existente:
            flash("Já existe uma área de cultivo com esse nome nesta propriedade.", "error")
            return render_template(
                "agricultura/nova_area_cultivo.html",
                propriedade=propriedade,
            )

        area_hectares = None
        if area_hectares_raw:
            try:
                area_hectares = float(area_hectares_raw.replace(",", "."))
            except ValueError:
                flash("Informe uma área válida em hectares.", "error")
                return render_template(
                    "agricultura/nova_area_cultivo.html",
                    propriedade=propriedade,
                )

        nova_area = AreaCultivo(
            propriedade_id=propriedade.id,
            nome=nome,
            tipo_area=tipo_area if tipo_area else None,
            area_hectares=area_hectares,
            observacoes=observacoes if observacoes else None,
            ativo=ativo,
            criado_em=datetime.utcnow(),
        )

        db.session.add(nova_area)
        db.session.commit()

        flash("Área de cultivo cadastrada com sucesso.", "success")
        return redirect(
            url_for("agricultura.painel_agricola", propriedade_id=propriedade.id)
        )

    return render_template(
        "agricultura/nova_area_cultivo.html",
        propriedade=propriedade,
    )


@agricultura_bp.route("/areas/<int:area_id>")
@login_obrigatorio
def detalhe_area_cultivo(area_id):
    usuario_id = session.get("usuario_id")
    usuario = Usuario.query.get(usuario_id)

    area = AreaCultivo.query.get_or_404(area_id)
    propriedade = area.propriedade

    if not usuario_tem_acesso_propriedade(usuario, propriedade):
        flash("Você não tem permissão para acessar esta área de cultivo.", "error")
        return redirect(url_for("main.painel"))

    ciclos = area.ciclos if hasattr(area, "ciclos") else []

    return render_template(
        "agricultura/detalhe_area_cultivo.html",
        area=area,
        propriedade=propriedade,
        ciclos=ciclos,
    )


@agricultura_bp.route("/areas/<int:area_id>/ciclos/novo", methods=["GET", "POST"])
@login_obrigatorio
def novo_ciclo_cultivo(area_id):
    usuario_id = session.get("usuario_id")
    usuario = Usuario.query.get(usuario_id)

    area = AreaCultivo.query.get_or_404(area_id)
    propriedade = area.propriedade

    if not usuario_tem_acesso_propriedade(usuario, propriedade):
        flash("Você não tem permissão para alterar esta área de cultivo.", "error")
        return redirect(url_for("main.painel"))

    if request.method == "POST":
        cultura = request.form.get("cultura", "").strip()
        variedade = request.form.get("variedade", "").strip()
        data_plantio_raw = request.form.get("data_plantio", "").strip()
        data_prevista_colheita_raw = request.form.get("data_prevista_colheita", "").strip()
        status = request.form.get("status", "em_andamento").strip()
        produtividade_estimada_raw = request.form.get("produtividade_estimada", "").strip()
        observacoes = request.form.get("observacoes", "").strip()

        if not cultura:
            flash("Informe a cultura do ciclo.", "error")
            return render_template(
                "agricultura/novo_ciclo_cultivo.html",
                area=area,
                propriedade=propriedade,
            )

        if not data_plantio_raw:
            flash("Informe a data de plantio.", "error")
            return render_template(
                "agricultura/novo_ciclo_cultivo.html",
                area=area,
                propriedade=propriedade,
            )

        try:
            data_plantio = datetime.strptime(data_plantio_raw, "%Y-%m-%d").date()
        except ValueError:
            flash("Informe uma data de plantio válida.", "error")
            return render_template(
                "agricultura/novo_ciclo_cultivo.html",
                area=area,
                propriedade=propriedade,
            )

        data_prevista_colheita = None
        if data_prevista_colheita_raw:
            try:
                data_prevista_colheita = datetime.strptime(
                    data_prevista_colheita_raw, "%Y-%m-%d"
                ).date()
            except ValueError:
                flash("Informe uma data prevista de colheita válida.", "error")
                return render_template(
                    "agricultura/novo_ciclo_cultivo.html",
                    area=area,
                    propriedade=propriedade,
                )

        produtividade_estimada = None
        if produtividade_estimada_raw:
            try:
                produtividade_estimada = float(
                    produtividade_estimada_raw.replace(",", ".")
                )
            except ValueError:
                flash("Informe uma produtividade estimada válida.", "error")
                return render_template(
                    "agricultura/novo_ciclo_cultivo.html",
                    area=area,
                    propriedade=propriedade,
                )

        novo_ciclo = CicloCultivo(
            area_cultivo_id=area.id,
            cultura=cultura,
            variedade=variedade if variedade else None,
            data_plantio=data_plantio,
            data_prevista_colheita=data_prevista_colheita,
            status=status if status else "em_andamento",
            produtividade_estimada=produtividade_estimada,
            observacoes=observacoes if observacoes else None,
            criado_em=datetime.utcnow(),
        )

        db.session.add(novo_ciclo)
        db.session.commit()

        flash("Ciclo de cultivo cadastrado com sucesso.", "success")
        return redirect(url_for("agricultura.detalhe_area_cultivo", area_id=area.id))

    return render_template(
        "agricultura/novo_ciclo_cultivo.html",
        area=area,
        propriedade=propriedade,
    )


@agricultura_bp.route("/ciclos/<int:ciclo_id>")
@login_obrigatorio
def detalhe_ciclo_cultivo(ciclo_id):
    usuario_id = session.get("usuario_id")
    usuario = Usuario.query.get(usuario_id)

    ciclo = CicloCultivo.query.get_or_404(ciclo_id)
    area = ciclo.area_cultivo
    propriedade = area.propriedade

    if not usuario_tem_acesso_propriedade(usuario, propriedade):
        flash("Você não tem permissão para acessar este ciclo de cultivo.", "error")
        return redirect(url_for("main.painel"))

    manejos = (
        ManejoAgricola.query
        .filter_by(ciclo_cultivo_id=ciclo.id)
        .order_by(ManejoAgricola.data_manejo.desc(), ManejoAgricola.criado_em.desc())
        .all()
    )

    return render_template(
        "agricultura/detalhe_ciclo_cultivo.html",
        ciclo=ciclo,
        area=area,
        propriedade=propriedade,
        manejos=manejos,
    )


@agricultura_bp.route("/ciclos/<int:ciclo_id>/manejos/novo", methods=["GET", "POST"])
@login_obrigatorio
def novo_manejo_agricola(ciclo_id):
    usuario_id = session.get("usuario_id")
    usuario = Usuario.query.get(usuario_id)

    ciclo = CicloCultivo.query.get_or_404(ciclo_id)
    area = ciclo.area_cultivo
    propriedade = area.propriedade

    if not usuario_tem_acesso_propriedade(usuario, propriedade):
        flash("Você não tem permissão para alterar este ciclo de cultivo.", "error")
        return redirect(url_for("main.painel"))

    if request.method == "POST":
        tipo_manejo = request.form.get("tipo_manejo", "").strip()
        data_manejo_raw = request.form.get("data_manejo", "").strip()
        responsavel = request.form.get("responsavel", "").strip()
        descricao = request.form.get("descricao", "").strip()

        if not tipo_manejo:
            flash("Informe o tipo de manejo.", "error")
            return render_template(
                "agricultura/novo_manejo_agricola.html",
                ciclo=ciclo,
                area=area,
                propriedade=propriedade,
            )

        if not data_manejo_raw:
            flash("Informe a data do manejo.", "error")
            return render_template(
                "agricultura/novo_manejo_agricola.html",
                ciclo=ciclo,
                area=area,
                propriedade=propriedade,
            )

        try:
            data_manejo = datetime.strptime(data_manejo_raw, "%Y-%m-%d").date()
        except ValueError:
            flash("Informe uma data de manejo válida.", "error")
            return render_template(
                "agricultura/novo_manejo_agricola.html",
                ciclo=ciclo,
                area=area,
                propriedade=propriedade,
            )

        novo_manejo = ManejoAgricola(
            ciclo_cultivo_id=ciclo.id,
            tipo_manejo=tipo_manejo,
            data_manejo=data_manejo,
            responsavel=responsavel if responsavel else None,
            descricao=descricao if descricao else None,
            criado_em=datetime.utcnow(),
        )

        db.session.add(novo_manejo)
        db.session.commit()

        flash("Manejo agrícola cadastrado com sucesso.", "success")
        return redirect(url_for("agricultura.detalhe_ciclo_cultivo", ciclo_id=ciclo.id))

    return render_template(
        "agricultura/novo_manejo_agricola.html",
        ciclo=ciclo,
        area=area,
        propriedade=propriedade,
    )


@agricultura_bp.route("/ciclos/<int:ciclo_id>/relatorio")
@login_obrigatorio
def relatorio_assistencia_tecnica_rural(ciclo_id):
    usuario_id = session.get("usuario_id")
    usuario = Usuario.query.get(usuario_id)

    ciclo = CicloCultivo.query.get_or_404(ciclo_id)
    area = ciclo.area_cultivo
    propriedade = area.propriedade

    if not usuario_tem_acesso_propriedade(usuario, propriedade):
        flash("Você não tem permissão para acessar este relatório.", "error")
        return redirect(url_for("main.painel"))

    manejos = (
        ManejoAgricola.query
        .filter_by(ciclo_cultivo_id=ciclo.id)
        .order_by(ManejoAgricola.data_manejo.asc(), ManejoAgricola.criado_em.asc())
        .all()
    )

    data_emissao = datetime.now()

    return render_template(
        "agricultura/relatorio_assistencia_tecnica_rural.html",
        ciclo=ciclo,
        area=area,
        propriedade=propriedade,
        manejos=manejos,
        data_emissao=data_emissao,
        usuario=usuario,
    )


@agricultura_bp.route("/ciclos/<int:ciclo_id>/relatorio/pdf")
@login_obrigatorio
def relatorio_assistencia_tecnica_rural_pdf(ciclo_id):
    usuario_id = session.get("usuario_id")
    usuario = Usuario.query.get(usuario_id)

    ciclo = CicloCultivo.query.get_or_404(ciclo_id)
    area = ciclo.area_cultivo
    propriedade = area.propriedade

    if not usuario_tem_acesso_propriedade(usuario, propriedade):
        flash("Você não tem permissão para acessar este relatório.", "error")
        return redirect(url_for("main.painel"))

    manejos = (
        ManejoAgricola.query
        .filter_by(ciclo_cultivo_id=ciclo.id)
        .order_by(ManejoAgricola.data_manejo.asc(), ManejoAgricola.criado_em.asc())
        .all()
    )

    config_sistema = (
        ConfiguracaoSistema.query
        .order_by(ConfiguracaoSistema.id.desc())
        .first()
    )

    logo_url = None
    if config_sistema and config_sistema.logo:
        caminho_logo = config_sistema.logo.strip()

        if caminho_logo.startswith("static/"):
            caminho_logo = caminho_logo.replace("static/", "", 1)

        if caminho_logo.startswith("/static/"):
            caminho_logo = caminho_logo.replace("/static/", "", 1)

        logo_url = url_for(
            "static",
            filename=caminho_logo,
            _external=True
        )

    gerado_em = datetime.now()

    html = render_template(
        "agricultura/relatorio_assistencia_tecnica_rural_pdf.html",
        ciclo=ciclo,
        area=area,
        propriedade=propriedade,
        manejos=manejos,
        usuario=usuario,
        gerado_em=gerado_em,
        config_sistema=config_sistema,
        logo_url=logo_url,
    )

    pdf = HTML(
        string=html,
        base_url=request.root_url
    ).write_pdf()

    nome_arquivo = f"relatorio_assistencia_tecnica_rural_ciclo_{ciclo.id}.pdf"

    return Response(
        pdf,
        mimetype="application/pdf",
        headers={
            "Content-Disposition": f"inline; filename={nome_arquivo}"
        }
    )