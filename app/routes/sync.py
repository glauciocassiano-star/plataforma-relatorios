from datetime import datetime

from flask import jsonify, request

from .base import main
from .. import db
from ..helpers.auth import obter_usuario_logado
from ..helpers.decorators import login_obrigatorio
from ..models import Atendimento


@main.route("/sync/atendimentos", methods=["POST"])
@login_obrigatorio
def sync_atendimentos():
    usuario = obter_usuario_logado()
    dados = request.get_json(silent=True)

    if not dados or not isinstance(dados, list):
        return jsonify({
            "sucesso": False,
            "erro": "Nenhum dado válido recebido."
        }), 400

    salvos = 0
    erros = []

    try:
        for item in dados:
            animal_id = item.get("_animal_id") or item.get("animal_id")
            formulario_id = item.get("_formulario_id") or item.get("formulario_id")
            data_atendimento_str = (item.get("data_atendimento") or "").strip()

            if not animal_id:
                erros.append("Registro ignorado: animal_id não informado.")
                continue

            data_atendimento = None
            if data_atendimento_str:
                try:
                    data_atendimento = datetime.strptime(
                        data_atendimento_str, "%Y-%m-%d"
                    ).date()
                except ValueError:
                    erros.append(
                        f"Registro do animal {animal_id} ignorado: data_atendimento inválida."
                    )
                    continue

            dados_formulario = dict(item)

            for chave in [
                "_offline_id",
                "_salvo_em",
                "_animal_id",
                "_formulario_id",
            ]:
                dados_formulario.pop(chave, None)

            novo_atendimento = Atendimento(
                animal_id=int(animal_id),
                tecnico_id=usuario.id,
                formulario_id=int(formulario_id) if formulario_id else None,
                data_atendimento=data_atendimento,
                dados=dados_formulario,
            )

            db.session.add(novo_atendimento)
            salvos += 1

        db.session.commit()

        return jsonify({
            "sucesso": True,
            "salvos": salvos,
            "erros": erros,
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({
            "sucesso": False,
            "erro": str(e),
        }), 500