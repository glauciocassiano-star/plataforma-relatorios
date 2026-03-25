from flask import render_template

from .base import main
from ..helpers.auth import obter_usuario_logado
from ..helpers.decorators import login_obrigatorio
from ..models import Animal, Atendimento
from ..services.propriedade_service import listar_propriedades_do_usuario


@main.route("/")
@login_obrigatorio
def painel():
    usuario = obter_usuario_logado()

    propriedades = listar_propriedades_do_usuario(usuario)
    propriedades_ids = [p.id for p in propriedades]

    if usuario.perfil == "admin":
        total_animais = Animal.query.count()
        atendimentos = Atendimento.query.all()
    else:
        total_animais = (
            Animal.query
            .filter(Animal.propriedade_id.in_(propriedades_ids))
            .count()
        )

        atendimentos = (
            Atendimento.query
            .join(Animal)
            .filter(Animal.propriedade_id.in_(propriedades_ids))
            .all()
        )

    total_atendimentos = len(atendimentos)

    contagem_diagnostico = {}
    contagem_mensal = {}

    for atendimento in atendimentos:
        dados = atendimento.dados if isinstance(atendimento.dados, dict) else {}
        diagnostico = (dados.get("diagnostico_principal") or "").strip()

        if diagnostico:
            contagem_diagnostico[diagnostico] = (
                contagem_diagnostico.get(diagnostico, 0) + 1
            )

        if atendimento.data_atendimento:
            chave_mes = atendimento.data_atendimento.strftime("%m/%Y")
            contagem_mensal[chave_mes] = contagem_mensal.get(chave_mes, 0) + 1

    diagnostico_mais_comum = None
    if contagem_diagnostico:
        diagnostico_mais_comum = max(contagem_diagnostico, key=contagem_diagnostico.get)

    def chave_ordenacao_mes(item):
        mes_ano = item[0]
        mes, ano = mes_ano.split("/")
        return (int(ano), int(mes))

    contagem_mensal = dict(sorted(contagem_mensal.items(), key=chave_ordenacao_mes))

    return render_template(
        "painel.html",
        propriedades=propriedades,
        total_propriedades=len(propriedades),
        total_animais=total_animais,
        total_atendimentos=total_atendimentos,
        diagnostico_mais_comum=diagnostico_mais_comum,
        contagem_mensal=contagem_mensal,
    )