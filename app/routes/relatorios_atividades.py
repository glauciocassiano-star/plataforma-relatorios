from datetime import datetime

from flask import Response, flash, redirect, render_template, request, url_for
from sqlalchemy.orm import joinedload
from weasyprint import HTML

from .base import main
from ..helpers.auth import obter_usuario_logado
from ..helpers.decorators import login_obrigatorio
from ..models import Atendimento, CampoFormulario, ConfiguracaoSistema, Formulario
from ..services.propriedade_service import listar_propriedades_do_usuario


def _montar_registros_relatorio(atendimentos):
    registros = []

    for atendimento in atendimentos:
        animal = atendimento.animal
        formulario = atendimento.formulario
        usuario = atendimento.tecnico

        campos_ordenados = []
        dados = atendimento.dados or {}

        if formulario:
            campos = (
                CampoFormulario.query
                .filter_by(formulario_id=formulario.id, visivel=True)
                .order_by(CampoFormulario.ordem.asc(), CampoFormulario.id.asc())
                .all()
            )

            for campo in campos:
                valor = dados.get(campo.nome_chave)

                if valor in [None, "", [], False]:
                    continue

                if isinstance(valor, list):
                    valor_formatado = ", ".join(str(v) for v in valor if v not in [None, ""])
                elif isinstance(valor, bool):
                    valor_formatado = "Sim" if valor else "Não"
                else:
                    valor_formatado = str(valor)

                campos_ordenados.append({
                    "rotulo": campo.rotulo,
                    "nome_chave": campo.nome_chave,
                    "valor": valor_formatado,
                })

        registros.append({
            "atendimento": atendimento,
            "animal": animal,
            "formulario": formulario,
            "usuario": usuario,
            "propriedade": animal.propriedade if animal else None,
            "campos": campos_ordenados,
        })

    return registros


@main.route("/relatorios/atividades", methods=["GET"])
@login_obrigatorio
def relatorio_atividades():
    usuario = obter_usuario_logado()
    propriedades = listar_propriedades_do_usuario(usuario)

    perfil = (request.args.get("perfil") or "").strip().lower()
    propriedade_id = request.args.get("propriedade_id", type=int)
    data_inicio = (request.args.get("data_inicio") or "").strip()
    data_fim = (request.args.get("data_fim") or "").strip()

    registros = []
    total_atendimentos = 0
    filtros_aplicados = False

    if perfil or propriedade_id or data_inicio or data_fim:
        filtros_aplicados = True

        query = (
            Atendimento.query
            .options(
                joinedload(Atendimento.animal).joinedload("propriedade"),
                joinedload(Atendimento.formulario),
                joinedload(Atendimento.tecnico),
            )
            .join(Formulario, Atendimento.formulario_id == Formulario.id)
        )

        if perfil in ["tecnico", "veterinario"]:
            query = query.filter(Formulario.perfil_alvo == perfil)

        if propriedade_id:
            query = query.join(Atendimento.animal).filter_by(propriedade_id=propriedade_id)

        if data_inicio:
            try:
                data_inicio_obj = datetime.strptime(data_inicio, "%Y-%m-%d").date()
                query = query.filter(Atendimento.data_atendimento >= data_inicio_obj)
            except ValueError:
                flash("Data inicial inválida.", "error")
                return redirect(url_for("main.relatorio_atividades"))

        if data_fim:
            try:
                data_fim_obj = datetime.strptime(data_fim, "%Y-%m-%d").date()
                query = query.filter(Atendimento.data_atendimento <= data_fim_obj)
            except ValueError:
                flash("Data final inválida.", "error")
                return redirect(url_for("main.relatorio_atividades"))

        atendimentos = (
            query.order_by(
                Atendimento.data_atendimento.desc(),
                Atendimento.criado_em.desc()
            ).all()
        )

        registros = _montar_registros_relatorio(atendimentos)
        total_atendimentos = len(registros)

    return render_template(
        "relatorio_atividades.html",
        propriedades=propriedades,
        perfil=perfil,
        propriedade_id=propriedade_id,
        data_inicio=data_inicio,
        data_fim=data_fim,
        registros=registros,
        total_atendimentos=total_atendimentos,
        filtros_aplicados=filtros_aplicados,
    )


@main.route("/relatorios/atividades/pdf", methods=["POST"])
@login_obrigatorio
def relatorio_atividades_pdf():
    usuario = obter_usuario_logado()
    propriedades = listar_propriedades_do_usuario(usuario)

    perfil = (request.form.get("perfil") or "").strip().lower()
    propriedade_id = request.form.get("propriedade_id", type=int)
    data_inicio = (request.form.get("data_inicio") or "").strip()
    data_fim = (request.form.get("data_fim") or "").strip()

    query = (
        Atendimento.query
        .options(
            joinedload(Atendimento.animal).joinedload("propriedade"),
            joinedload(Atendimento.formulario),
            joinedload(Atendimento.tecnico),
        )
        .join(Formulario, Atendimento.formulario_id == Formulario.id)
    )

    if perfil in ["tecnico", "veterinario"]:
        query = query.filter(Formulario.perfil_alvo == perfil)

    if propriedade_id:
        query = query.join(Atendimento.animal).filter_by(propriedade_id=propriedade_id)

    if data_inicio:
        try:
            data_inicio_obj = datetime.strptime(data_inicio, "%Y-%m-%d").date()
            query = query.filter(Atendimento.data_atendimento >= data_inicio_obj)
        except ValueError:
            flash("Data inicial inválida.", "error")
            return redirect(url_for("main.relatorio_atividades"))

    if data_fim:
        try:
            data_fim_obj = datetime.strptime(data_fim, "%Y-%m-%d").date()
            query = query.filter(Atendimento.data_atendimento <= data_fim_obj)
        except ValueError:
            flash("Data final inválida.", "error")
            return redirect(url_for("main.relatorio_atividades"))

    atendimentos = (
        query.order_by(
            Atendimento.data_atendimento.desc(),
            Atendimento.criado_em.desc()
        ).all()
    )

    registros = _montar_registros_relatorio(atendimentos)
    config_sistema = (
        ConfiguracaoSistema.query
        .order_by(ConfiguracaoSistema.id.desc())
        .first()
    )

    propriedade_nome = None
    if propriedade_id:
        prop = next((p for p in propriedades if p.id == propriedade_id), None)
        if prop:
            propriedade_nome = prop.nome

    html = render_template(
        "relatorio_atividades_pdf.html",
        registros=registros,
        perfil=perfil,
        propriedade_nome=propriedade_nome,
        data_inicio=data_inicio,
        data_fim=data_fim,
        config_sistema=config_sistema,
        gerado_em=datetime.now(),
        total_atendimentos=len(registros),
    )

    pdf = HTML(string=html).write_pdf()

    return Response(
        pdf,
        mimetype="application/pdf",
        headers={
            "Content-Disposition": "inline; filename=relatorio_atividades.pdf"
        },
    )