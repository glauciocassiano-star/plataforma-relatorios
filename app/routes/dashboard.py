from datetime import date

from flask import render_template, redirect, url_for, session

from .base import main
from ..helpers.auth import obter_usuario_logado
from ..helpers.decorators import login_obrigatorio
from ..models import Animal, Atendimento, ConfiguracaoSistema, Usuario
from ..services.propriedade_service import listar_propriedades_do_usuario


@main.route("/")
def index():
    if session.get("usuario_id"):
        return redirect(url_for("main.painel"))

    config = (
        ConfiguracaoSistema.query
        .order_by(ConfiguracaoSistema.id.desc())
        .first()
    )

    return render_template(
        "landing.html",
        config=config,
        modo_login=False,
        ocultar_layout=True,
    )


@main.route("/painel")
@login_obrigatorio
def painel():
    usuario = obter_usuario_logado()

    propriedades = listar_propriedades_do_usuario(usuario)
    propriedades_ids = [p.id for p in propriedades]

    perfil_usuario = (usuario.perfil or "").strip().lower()

    # Perfis com visão ampliada
    usuario_eh_admin = perfil_usuario in ["admin", "admin_master", "admin_cliente"]

    if usuario_eh_admin:
        total_animais = Animal.query.count()
        atendimentos = Atendimento.query.all()
        total_profissionais_ativos = (
            Usuario.query
            .filter(Usuario.ativo.is_(True))
            .count()
        )
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

        total_profissionais_ativos = 1

    total_atendimentos = len(atendimentos)

    contagem_diagnostico = {}
    contagem_mensal = {}
    contagem_formulario = {}
    contagem_perfil = {}
    contagem_propriedade = {}
    atendimentos_mes_atual = 0

    hoje = date.today()
    mes_atual = hoje.month
    ano_atual = hoje.year

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

            if (
                atendimento.data_atendimento.month == mes_atual
                and atendimento.data_atendimento.year == ano_atual
            ):
                atendimentos_mes_atual += 1

        if atendimento.formulario:
            nome_formulario = (atendimento.formulario.nome or "").strip()
            perfil_alvo = (atendimento.formulario.perfil_alvo or "").strip()

            if nome_formulario:
                contagem_formulario[nome_formulario] = (
                    contagem_formulario.get(nome_formulario, 0) + 1
                )

            if perfil_alvo:
                contagem_perfil[perfil_alvo] = (
                    contagem_perfil.get(perfil_alvo, 0) + 1
                )

        if atendimento.animal and atendimento.animal.propriedade:
            nome_propriedade = (atendimento.animal.propriedade.nome or "").strip()
            if nome_propriedade:
                contagem_propriedade[nome_propriedade] = (
                    contagem_propriedade.get(nome_propriedade, 0) + 1
                )

    diagnostico_mais_comum = None
    if contagem_diagnostico:
        diagnostico_mais_comum = max(contagem_diagnostico, key=contagem_diagnostico.get)

    formulario_mais_utilizado = None
    if contagem_formulario:
        formulario_mais_utilizado = max(contagem_formulario, key=contagem_formulario.get)

    perfil_mais_atuante = None
    if contagem_perfil:
        perfil_mais_atuante = max(contagem_perfil, key=contagem_perfil.get)

    propriedade_mais_assistida = None
    if contagem_propriedade:
        propriedade_mais_assistida = max(contagem_propriedade, key=contagem_propriedade.get)

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
        atendimentos_mes_atual=atendimentos_mes_atual,
        total_profissionais_ativos=total_profissionais_ativos,
        diagnostico_mais_comum=diagnostico_mais_comum,
        formulario_mais_utilizado=formulario_mais_utilizado,
        perfil_mais_atuante=perfil_mais_atuante,
        propriedade_mais_assistida=propriedade_mais_assistida,
        contagem_mensal=contagem_mensal,
    )