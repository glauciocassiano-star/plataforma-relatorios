from __future__ import annotations

from typing import Optional

from app import db
from app.models import Formulario, CampoFormulario


CONTEXTOS_VALIDOS = {"rural", "clinica", "hospital"}


def normalizar_contexto(tipo_contexto: Optional[str]) -> str:
    """
    Garante que o contexto do formulário esteja em um valor suportado.
    """
    if not tipo_contexto:
        return "rural"

    valor = str(tipo_contexto).strip().lower()
    return valor if valor in CONTEXTOS_VALIDOS else "rural"


def obter_formulario_ativo(
    *,
    tipo_contexto: str,
    perfil: str,
    cliente_id: Optional[int] = None,
    perfil_usuario_logado: Optional[str] = None,
) -> Optional[Formulario]:
    """
    Retorna o formulário ativo mais adequado para o contexto/perfil.

    Regras:
    - admin_master:
        acesso irrestrito aos formulários ativos compatíveis
    - admin_cliente / tecnico / veterinario:
        1. formulário personalizado do cliente
        2. template-base do sistema
    """
    contexto = normalizar_contexto(tipo_contexto)
    perfil_normalizado = (perfil or "").strip().lower()
    perfil_usuario_logado = (perfil_usuario_logado or "").strip().lower()

    query_base = Formulario.query.filter(
        Formulario.ativo.is_(True),
        Formulario.tipo_contexto == contexto,
    ).filter(
        (Formulario.perfil_alvo == perfil_normalizado) |
        (Formulario.perfil_alvo == "ambos")
    )

    # ADMIN MASTER: acesso irrestrito
    if perfil_usuario_logado == "admin_master":
        # 1. tenta qualquer formulário personalizado compatível
        formulario_personalizado = (
            query_base
            .filter(Formulario.template_base.is_(False))
            .order_by(Formulario.id.desc())
            .first()
        )
        if formulario_personalizado:
            return formulario_personalizado

        # 2. fallback para template base
        formulario_base = (
            query_base
            .filter(Formulario.template_base.is_(True))
            .order_by(Formulario.id.desc())
            .first()
        )
        return formulario_base

    # USUÁRIOS COM CLIENTE: prioriza o formulário do cliente
    if cliente_id:
        formulario_cliente = (
            query_base
            .filter(
                Formulario.cliente_id == cliente_id,
                Formulario.template_base.is_(False),
            )
            .order_by(Formulario.id.desc())
            .first()
        )
        if formulario_cliente:
            return formulario_cliente

    # FALLBACK: template-base do sistema
    formulario_base = (
        query_base
        .filter(Formulario.template_base.is_(True))
        .order_by(Formulario.id.desc())
        .first()
    )
    return formulario_base


def listar_campos_formulario(formulario_id: int) -> list[CampoFormulario]:
    """
    Retorna os campos visíveis de um formulário em ordem de exibição.
    """
    return (
        CampoFormulario.query
        .filter_by(formulario_id=formulario_id, visivel=True)
        .order_by(CampoFormulario.ordem.asc(), CampoFormulario.id.asc())
        .all()
    )


def clonar_formulario_base(
    *,
    formulario_base_id: int,
    cliente_id: int,
    novo_nome: Optional[str] = None,
    ativo: bool = True,
) -> Formulario:
    """
    Duplica um template-base e todos os seus campos para uso personalizado por cliente.
    """
    formulario_base = Formulario.query.get_or_404(formulario_base_id)

    novo_formulario = Formulario(
        nome=novo_nome or f"{formulario_base.nome} - Personalizado",
        perfil_alvo=formulario_base.perfil_alvo,
        ativo=ativo,
        tipo_contexto=formulario_base.tipo_contexto,
        template_base=False,
        usa_sensor_mastite=getattr(formulario_base, "usa_sensor_mastite", False),
        sensor_obrigatorio=getattr(formulario_base, "sensor_obrigatorio", False),
        cliente_id=cliente_id,
        formulario_origem_id=formulario_base.id,
    )
    db.session.add(novo_formulario)
    db.session.flush()

    campos_base = (
        CampoFormulario.query
        .filter_by(formulario_id=formulario_base.id)
        .order_by(CampoFormulario.ordem.asc(), CampoFormulario.id.asc())
        .all()
    )

    for campo in campos_base:
        novo_campo = CampoFormulario(
            formulario_id=novo_formulario.id,
            rotulo=campo.rotulo,
            nome_chave=campo.nome_chave,
            tipo=campo.tipo,
            obrigatorio=campo.obrigatorio,
            opcoes=campo.opcoes,
            ordem=campo.ordem,
            grupo=getattr(campo, "grupo", None),
            ajuda=getattr(campo, "ajuda", None),
            placeholder=getattr(campo, "placeholder", None),
            visivel=getattr(campo, "visivel", True),
            editavel=getattr(campo, "editavel", True),
        )
        db.session.add(novo_campo)

    db.session.commit()
    return novo_formulario


def formulario_eh_editavel(formulario: Formulario) -> bool:
    """
    Template-base não deve ser editado diretamente pelo cliente.
    """
    return not bool(getattr(formulario, "template_base", False))


def atualizar_ordem_campos(formulario_id: int, campos_ordenados: list[int]) -> None:
    """
    Atualiza a ordem de exibição dos campos de um formulário.
    """
    campos = (
        CampoFormulario.query
        .filter(CampoFormulario.formulario_id == formulario_id)
        .all()
    )

    mapa = {campo.id: campo for campo in campos}

    for indice, campo_id in enumerate(campos_ordenados, start=1):
        campo = mapa.get(campo_id)
        if campo:
            campo.ordem = indice

    db.session.commit()
