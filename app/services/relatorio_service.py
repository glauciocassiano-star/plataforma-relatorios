from datetime import datetime, timedelta

from ..models import Animal, Atendimento, Propriedade, Exame
from ..services.propriedade_service import listar_propriedades_do_usuario


def gerar_relatorio_epidemiologico(
    usuario,
    propriedade_id=None,
    data_inicio=None,
    data_fim=None,
    somente_confirmados=None,
):
    data_inicio_convertida = None
    data_fim_convertida = None

    if usuario.perfil == "admin":
        propriedades = Propriedade.query.order_by(Propriedade.nome.asc()).all()
    else:
        propriedades = listar_propriedades_do_usuario(usuario)

    propriedades_ids = [p.id for p in propriedades]

    if usuario.perfil != "admin" and propriedade_id and propriedade_id not in propriedades_ids:
        raise ValueError("Você não tem acesso a essa propriedade.")

    query_animais = Animal.query

    if usuario.perfil == "admin":
        if propriedade_id:
            query_animais = query_animais.filter(Animal.propriedade_id == propriedade_id)
    else:
        query_animais = query_animais.filter(Animal.propriedade_id.in_(propriedades_ids))
        if propriedade_id:
            query_animais = query_animais.filter(Animal.propriedade_id == propriedade_id)

    animais_escopo = query_animais.all()

    contagem_animais_por_perfil = {}

    for animal in animais_escopo:
        perfil = (animal.perfil_genetico or "Não informado").strip()
        contagem_animais_por_perfil[perfil] = contagem_animais_por_perfil.get(perfil, 0) + 1

    query = (
        Atendimento.query
        .join(Animal, Atendimento.animal_id == Animal.id)
        .join(Propriedade, Animal.propriedade_id == Propriedade.id)
    )

    if usuario.perfil == "admin":
        if propriedade_id:
            query = query.filter(Animal.propriedade_id == propriedade_id)
    else:
        query = query.filter(Animal.propriedade_id.in_(propriedades_ids))
        if propriedade_id:
            query = query.filter(Animal.propriedade_id == propriedade_id)

    if data_inicio:
        try:
            data_inicio_convertida = datetime.strptime(data_inicio, "%Y-%m-%d").date()
            query = query.filter(Atendimento.data_atendimento >= data_inicio_convertida)
        except ValueError:
            raise ValueError("Data inicial inválida.")

    if data_fim:
        try:
            data_fim_convertida = datetime.strptime(data_fim, "%Y-%m-%d").date()
            query = query.filter(Atendimento.data_atendimento <= data_fim_convertida)
        except ValueError:
            raise ValueError("Data final inválida.")

    if somente_confirmados:
        query = query.filter(
            Atendimento.exames.any(
                Exame.resultado.isnot(None)
            )
        )

    atendimentos = query.all()

    contagem_diagnostico = {}
    contagem_categoria = {}
    contagem_desfecho = {}
    contagem_mensal = {}
    contagem_propriedade = {}
    contagem_genetica = {}
    contagem_confirmados = {}
    correlacao_genetica = {}
    probabilidade_base = {}

    for atendimento in atendimentos:
        dados = atendimento.dados if isinstance(atendimento.dados, dict) else {}

        diagnostico = (dados.get("diagnostico_principal") or "").strip()
        categoria = (dados.get("categoria_diagnostico") or "").strip()
        desfecho = (dados.get("desfecho") or "").strip()

        if diagnostico:
            contagem_diagnostico[diagnostico] = (
                contagem_diagnostico.get(diagnostico, 0) + 1
            )

        if categoria:
            contagem_categoria[categoria] = (
                contagem_categoria.get(categoria, 0) + 1
            )

        if desfecho:
            contagem_desfecho[desfecho] = (
                contagem_desfecho.get(desfecho, 0) + 1
            )

        if atendimento.data_atendimento:
            chave_mes = atendimento.data_atendimento.strftime("%m/%Y")
            contagem_mensal[chave_mes] = contagem_mensal.get(chave_mes, 0) + 1

        if atendimento.animal and atendimento.animal.propriedade:
            nome_propriedade = atendimento.animal.propriedade.nome
            contagem_propriedade[nome_propriedade] = (
                contagem_propriedade.get(nome_propriedade, 0) + 1
            )

        if diagnostico and atendimento.animal:
            perfil = (atendimento.animal.perfil_genetico or "Não informado").strip()

            chave = f"{perfil} | {diagnostico}"
            contagem_genetica[chave] = contagem_genetica.get(chave, 0) + 1

            if diagnostico not in correlacao_genetica:
                correlacao_genetica[diagnostico] = {
                    "total": 0,
                    "perfis": {}
                }

            correlacao_genetica[diagnostico]["total"] += 1
            correlacao_genetica[diagnostico]["perfis"][perfil] = (
                correlacao_genetica[diagnostico]["perfis"].get(perfil, 0) + 1
            )

            if diagnostico not in probabilidade_base:
                probabilidade_base[diagnostico] = {}

            probabilidade_base[diagnostico][perfil] = (
                probabilidade_base[diagnostico].get(perfil, 0) + 1
            )

        if diagnostico and getattr(atendimento, "exames", None):
            exames_com_resultado = [
                ex for ex in atendimento.exames
                if ex.resultado and ex.resultado.strip()
            ]

            if exames_com_resultado:
                contagem_confirmados[diagnostico] = (
                    contagem_confirmados.get(diagnostico, 0) + 1
                )

    contagem_diagnostico = dict(
        sorted(contagem_diagnostico.items(), key=lambda x: x[1], reverse=True)
    )
    contagem_categoria = dict(
        sorted(contagem_categoria.items(), key=lambda x: x[1], reverse=True)
    )
    contagem_desfecho = dict(
        sorted(contagem_desfecho.items(), key=lambda x: x[1], reverse=True)
    )
    contagem_propriedade = dict(
        sorted(contagem_propriedade.items(), key=lambda x: x[1], reverse=True)
    )
    contagem_genetica = dict(
        sorted(contagem_genetica.items(), key=lambda x: x[1], reverse=True)
    )

    def ordenar_mes(item):
        mes, ano = item[0].split("/")
        return (int(ano), int(mes))

    contagem_mensal = dict(sorted(contagem_mensal.items(), key=ordenar_mes))

    taxa_confirmacao = {}

    for diagnostico, total in contagem_diagnostico.items():
        confirmados = contagem_confirmados.get(diagnostico, 0)

        if total > 0:
            taxa = round((confirmados / total) * 100, 2)
        else:
            taxa = 0

        taxa_confirmacao[diagnostico] = {
            "total": total,
            "confirmados": confirmados,
            "taxa": taxa,
        }

    correlacao_genetica_resumo = {}

    for diagnostico, info in correlacao_genetica.items():
        perfis_ordenados = dict(
            sorted(info["perfis"].items(), key=lambda x: x[1], reverse=True)
        )

        perfil_top = None
        percentual_top = 0

        if perfis_ordenados:
            perfil_top = next(iter(perfis_ordenados))
            total_top = perfis_ordenados[perfil_top]

            if info["total"] > 0:
                percentual_top = round((total_top / info["total"]) * 100, 2)

        correlacao_genetica_resumo[diagnostico] = {
            "total": info["total"],
            "perfis": perfis_ordenados,
            "perfil_top": perfil_top,
            "percentual_top": percentual_top,
        }

    probabilidade_ocorrencia = {}

    for diagnostico, perfis_dict in probabilidade_base.items():
        linhas = []

        for perfil, casos in perfis_dict.items():
            total_animais = contagem_animais_por_perfil.get(perfil, 0)

            if total_animais > 0:
                probabilidade = round((casos / total_animais) * 100, 2)
            else:
                probabilidade = 0

            linhas.append({
                "perfil": perfil,
                "casos": casos,
                "total_animais": total_animais,
                "probabilidade": probabilidade,
            })

        linhas = sorted(linhas, key=lambda x: x["probabilidade"], reverse=True)
        probabilidade_ocorrencia[diagnostico] = linhas

    propriedade_selecionada = None
    if propriedade_id:
        propriedade_selecionada = next(
            (p for p in propriedades if p.id == propriedade_id),
            None
        )

    if propriedade_id:
        propriedades_para_risco = [p for p in propriedades if p.id == propriedade_id]
    else:
        propriedades_para_risco = propriedades

    risco_propriedades = []

    hoje = datetime.now().date()
    inicio_30 = hoje - timedelta(days=30)
    inicio_60 = hoje - timedelta(days=60)

    for prop in propriedades_para_risco:
        total_animais_prop = Animal.query.filter_by(propriedade_id=prop.id).count()

        total_atendimentos_prop_query = (
            Atendimento.query
            .join(Animal, Atendimento.animal_id == Animal.id)
            .filter(Animal.propriedade_id == prop.id)
        )

        if data_inicio_convertida:
            total_atendimentos_prop_query = total_atendimentos_prop_query.filter(
                Atendimento.data_atendimento >= data_inicio_convertida
            )

        if data_fim_convertida:
            total_atendimentos_prop_query = total_atendimentos_prop_query.filter(
                Atendimento.data_atendimento <= data_fim_convertida
            )

        if somente_confirmados:
            total_atendimentos_prop_query = total_atendimentos_prop_query.filter(
                Atendimento.exames.any(
                    Exame.resultado.isnot(None)
                )
            )

        total_atendimentos_prop = total_atendimentos_prop_query.count()

        taxa = 0
        if total_animais_prop > 0:
            taxa = round((total_atendimentos_prop / total_animais_prop) * 100, 2)

        if taxa <= 20:
            classificacao = "Baixo"
        elif taxa <= 50:
            classificacao = "Moderado"
        else:
            classificacao = "Alto"

        ultimos_30_query = (
            Atendimento.query
            .join(Animal, Atendimento.animal_id == Animal.id)
            .filter(Animal.propriedade_id == prop.id)
            .filter(Atendimento.data_atendimento >= inicio_30)
        )

        anteriores_30_query = (
            Atendimento.query
            .join(Animal, Atendimento.animal_id == Animal.id)
            .filter(Animal.propriedade_id == prop.id)
            .filter(
                Atendimento.data_atendimento >= inicio_60,
                Atendimento.data_atendimento < inicio_30
            )
        )

        if somente_confirmados:
            ultimos_30_query = ultimos_30_query.filter(
                Atendimento.exames.any(
                    Exame.resultado.isnot(None)
                )
            )
            anteriores_30_query = anteriores_30_query.filter(
                Atendimento.exames.any(
                    Exame.resultado.isnot(None)
                )
            )

        ultimos_30 = ultimos_30_query.count()
        anteriores_30 = anteriores_30_query.count()

        tendencia = "Estável"

        if anteriores_30 > 0:
            variacao = ((ultimos_30 - anteriores_30) / anteriores_30) * 100

            if variacao > 20:
                tendencia = "Subindo"
            elif variacao < -20:
                tendencia = "Caindo"
        elif ultimos_30 > 0:
            tendencia = "Subindo"

        risco_propriedades.append({
            "nome": prop.nome,
            "total_animais": total_animais_prop,
            "total_atendimentos": total_atendimentos_prop,
            "taxa": taxa,
            "classificacao": classificacao,
            "tendencia": tendencia,
            "ultimos_30": ultimos_30,
            "anteriores_30": anteriores_30,
        })

    risco_propriedades = sorted(
        risco_propriedades,
        key=lambda x: x["taxa"],
        reverse=True
    )

    diagnostico_top = (
        max(contagem_diagnostico, key=contagem_diagnostico.get)
        if contagem_diagnostico else None
    )
    propriedade_top = (
        max(contagem_propriedade, key=contagem_propriedade.get)
        if contagem_propriedade else None
    )
    genetica_top = (
        max(contagem_genetica, key=contagem_genetica.get)
        if contagem_genetica else None
    )

    return {
        "contagem_diagnostico": contagem_diagnostico,
        "contagem_categoria": contagem_categoria,
        "contagem_desfecho": contagem_desfecho,
        "contagem_mensal": contagem_mensal,
        "contagem_propriedade": contagem_propriedade,
        "contagem_genetica": contagem_genetica,
        "correlacao_genetica_resumo": correlacao_genetica_resumo,
        "probabilidade_ocorrencia": probabilidade_ocorrencia,
        "contagem_confirmados": contagem_confirmados,
        "taxa_confirmacao": taxa_confirmacao,
        "risco_propriedades": risco_propriedades,
        "diagnostico_top": diagnostico_top,
        "propriedade_top": propriedade_top,
        "genetica_top": genetica_top,
        "total_atendimentos": len(atendimentos),
        "propriedades": propriedades,
        "propriedade_id": propriedade_id,
        "propriedade_selecionada": propriedade_selecionada,
        "data_inicio": data_inicio,
        "data_fim": data_fim,
        "somente_confirmados": somente_confirmados,
    }