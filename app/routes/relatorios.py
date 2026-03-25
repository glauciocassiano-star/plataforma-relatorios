from datetime import datetime

from flask import Response, flash, redirect, render_template, request, url_for
from weasyprint import HTML

from .base import main
from ..helpers.auth import obter_usuario_logado
from ..helpers.decorators import login_obrigatorio
from ..models import ConfiguracaoSistema
from ..services.relatorio_service import gerar_relatorio_epidemiologico


@main.route("/relatorios/epidemiologico")
@login_obrigatorio
def relatorio_epidemiologico():
    usuario = obter_usuario_logado()

    propriedade_id = request.args.get("propriedade_id", type=int)
    data_inicio = request.args.get("data_inicio")
    data_fim = request.args.get("data_fim")

    try:
        dados = gerar_relatorio_epidemiologico(
            usuario=usuario,
            propriedade_id=propriedade_id,
            data_inicio=data_inicio,
            data_fim=data_fim,
        )
    except ValueError as e:
        flash(str(e), "error")
        return redirect(url_for("main.relatorio_epidemiologico"))

    return render_template(
        "relatorio_epidemiologico.html",
        **dados
    )


@main.route("/relatorios/epidemiologico/pdf", methods=["POST"])
@login_obrigatorio
def relatorio_epidemiologico_pdf():
    usuario = obter_usuario_logado()

    propriedade_id = request.form.get("propriedade_id", type=int)
    data_inicio = request.form.get("data_inicio")
    data_fim = request.form.get("data_fim")
    somente_confirmados = request.form.get("somente_confirmados")

    grafico_diagnostico_img = request.form.get("grafico_diagnostico_img")
    grafico_mensal_img = request.form.get("grafico_mensal_img")

    try:
        dados = gerar_relatorio_epidemiologico(
            usuario=usuario,
            propriedade_id=propriedade_id,
            data_inicio=data_inicio,
            data_fim=data_fim,
            somente_confirmados=somente_confirmados,
        )
    except ValueError as e:
        flash(str(e), "error")
        return redirect(url_for("main.relatorio_epidemiologico"))

    config_sistema = ConfiguracaoSistema.query.first()

    html = render_template(
        "relatorio_epidemiologico_pdf.html",
        **dados,
        grafico_diagnostico_img=grafico_diagnostico_img,
        grafico_mensal_img=grafico_mensal_img,
        config_sistema=config_sistema,
        gerado_em=datetime.now(),
    )

    pdf = HTML(string=html).write_pdf()

    return Response(
        pdf,
        mimetype="application/pdf",
        headers={
            "Content-Disposition": "inline; filename=relatorio_epidemiologico.pdf"
        }
    )