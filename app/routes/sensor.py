from datetime import datetime

from flask import flash, redirect, render_template, request, url_for

from .base import main
from .. import db
from ..helpers.auth import obter_usuario_logado
from ..helpers.decorators import (
    acesso_animal,
    acesso_atendimento,
    acesso_sensor_obrigatorio,
    login_obrigatorio,
)
from ..models import Animal, Atendimento, LeituraSensor
from ..services.sensor_service import inferir_probabilidade_mastite


def _normalizar_float(valor, campo):
    valor = (valor or "").strip()
    if not valor:
        raise ValueError(f"O campo '{campo}' é obrigatório.")

    try:
        return float(valor)
    except ValueError as exc:
        raise ValueError(f"O campo '{campo}' deve ser numérico.") from exc


def _normalizar_int(valor, campo):
    valor = (valor or "").strip()
    if not valor:
        raise ValueError(f"O campo '{campo}' é obrigatório.")

    try:
        return int(valor)
    except ValueError as exc:
        raise ValueError(f"O campo '{campo}' deve ser inteiro.") from exc


@main.route("/atendimentos/<int:atendimento_id>/sensor/nova-leitura", methods=["GET", "POST"])
@login_obrigatorio
@acesso_atendimento
@acesso_sensor_obrigatorio
def nova_leitura_sensor(atendimento_id):
    atendimento = Atendimento.query.get_or_404(atendimento_id)
    animal = Animal.query.get_or_404(atendimento.animal_id)
    usuario = obter_usuario_logado()

    if request.method == "POST":
        try:
            condutividade = _normalizar_float(request.form.get("condutividade"), "Condutividade")
            temperatura = _normalizar_float(request.form.get("temperatura"), "Temperatura")
            variacao = _normalizar_float(request.form.get("variacao"), "Variação")
            consistencia = _normalizar_float(request.form.get("consistencia"), "Consistência")
            quantidade_leituras = _normalizar_int(
                request.form.get("quantidade_leituras"),
                "Quantidade de leituras",
            )
        except ValueError as erro:
            flash(str(erro), "error")
            return redirect(request.url)

        quarto_mamario = (request.form.get("quarto_mamario") or "").strip() or None
        observacoes = (request.form.get("observacoes") or "").strip() or None

        resultado = inferir_probabilidade_mastite(
            condutividade=condutividade,
            temperatura=temperatura,
            variacao=variacao,
            consistencia=consistencia,
            quantidade_leituras=quantidade_leituras,
        )

        leitura = LeituraSensor(
            cliente_id=getattr(usuario, "cliente_id", None),
            propriedade_id=animal.propriedade_id,
            animal_id=animal.id,
            atendimento_id=atendimento.id,
            usuario_id=usuario.id,
            quarto_mamario=quarto_mamario,
            condutividade=condutividade,
            temperatura=temperatura,
            variacao=variacao,
            consistencia=consistencia,
            quantidade_leituras=quantidade_leituras,
            risco_estimado=resultado["risco_estimado"],
            confianca=resultado["confianca"],
            intervalo_inferior=resultado["intervalo_inferior"],
            intervalo_superior=resultado["intervalo_superior"],
            classificacao=resultado["classificacao"],
            recomendacao=resultado["recomendacao"],
            observacoes=observacoes,
            dados_brutos={
                "classificacao_rotulo": resultado["classificacao_rotulo"],
                "capturado_em": datetime.utcnow().isoformat(),
            },
        )

        db.session.add(leitura)
        db.session.commit()

        flash("Leitura do sensor registrada com sucesso.", "success")
        return redirect(url_for("main.prontuario_animal", animal_id=animal.id))

    return render_template(
        "sensor_nova_leitura.html",
        atendimento=atendimento,
        animal=animal,
    )
