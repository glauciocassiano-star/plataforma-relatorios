from __future__ import annotations

from typing import Any


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return min(max(value, minimum), maximum)


def _ajuste_temperatura(temperatura: float) -> float:
    ideal = 25.0
    delta = abs(temperatura - ideal)
    if delta <= 2:
        return 0.0
    return delta * 1.4


def classificar_risco(score: float) -> dict[str, str]:
    if score < 35:
        return {
            "faixa": "baixo_indicativo",
            "rotulo": "Baixo indicativo",
            "recomendacao": (
                "Manter monitoramento de rotina e repetir a leitura se houver "
                "mudança clínica ou histórico recente."
            ),
        }

    if score < 65:
        return {
            "faixa": "indicativo_moderado",
            "rotulo": "Indicativo moderado",
            "recomendacao": (
                "Repetir a sequência de leituras e acompanhar o animal. Se o padrão "
                "persistir, recomendar confirmação laboratorial."
            ),
        }

    return {
        "faixa": "alto_indicativo",
        "rotulo": "Alto indicativo",
        "recomendacao": (
            "O padrão inflamatório é relevante. Recomenda-se confirmação "
            "laboratorial e avaliação clínica complementar."
        ),
    }


def inferir_probabilidade_mastite(
    *,
    condutividade: float,
    temperatura: float,
    variacao: float,
    consistencia: float,
    quantidade_leituras: int,
) -> dict[str, Any]:
    impacto_condutividade = _clamp((condutividade - 4.7) * 18, 0, 55)
    impacto_variacao = _clamp(variacao * 2.1, 0, 25)
    penalidade_temperatura = _clamp(_ajuste_temperatura(temperatura), 0, 18)
    bonus_repeticao = _clamp((quantidade_leituras - 1) * 4, 0, 16)
    bonus_consistencia = _clamp((consistencia - 55) * 0.45, 0, 20)

    score_bruto = (
        impacto_condutividade
        + impacto_variacao
        + bonus_repeticao
        + bonus_consistencia
        - penalidade_temperatura
    )

    risco = _clamp(score_bruto, 0, 99)
    confianca = _clamp(
        35 + bonus_repeticao + bonus_consistencia - penalidade_temperatura * 0.8,
        20,
        96,
    )
    intervalo = _clamp((100 - confianca) * 0.35, 4, 28)
    classificacao = classificar_risco(risco)

    return {
        "risco_estimado": round(risco, 2),
        "confianca": round(confianca, 2),
        "intervalo_inferior": round(max(risco - intervalo, 0), 2),
        "intervalo_superior": round(min(risco + intervalo, 100), 2),
        "classificacao": classificacao["faixa"],
        "classificacao_rotulo": classificacao["rotulo"],
        "recomendacao": classificacao["recomendacao"],
    }
