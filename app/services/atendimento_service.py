from __future__ import annotations

from datetime import datetime

from .. import db
from ..helpers.uploads import arquivo_imagem_permitido, salvar_imagem_atendimento
from ..models import AtendimentoImagem


def processar_dados_formulario(campos, form):
    """
    Processa e valida os dados dinâmicos do formulário.
    Compatível com:
    - text
    - textarea
    - number
    - checkbox (booleano ou múltipla escolha)
    - select
    - date
    - datetime
    """
    dados = {}

    for c in campos:
        valor = None

        if c.tipo == "checkbox":
            # Se houver opções, tratamos como múltipla escolha
            if c.opcoes:
                valor = form.getlist(c.nome_chave)
                valor = [v.strip() for v in valor if v and v.strip()]
                if not valor:
                    valor = []
            else:
                # checkbox simples (true/false)
                valor = True if form.get(c.nome_chave) else False

        elif c.tipo == "number":
            bruto = (form.get(c.nome_chave) or "").strip()
            if bruto == "":
                valor = None
            else:
                try:
                    valor = float(bruto) if "." in bruto else int(bruto)
                except ValueError:
                    raise ValueError(f"O campo '{c.rotulo}' deve ser numérico.")

        elif c.tipo == "date":
            bruto = (form.get(c.nome_chave) or "").strip()
            if bruto == "":
                valor = None
            else:
                try:
                    datetime.strptime(bruto, "%Y-%m-%d")
                    valor = bruto
                except ValueError:
                    raise ValueError(f"O campo '{c.rotulo}' deve ser uma data válida.")

        elif c.tipo == "datetime":
            bruto = (form.get(c.nome_chave) or "").strip()
            if bruto == "":
                valor = None
            else:
                try:
                    datetime.strptime(bruto, "%Y-%m-%dT%H:%M")
                    valor = bruto
                except ValueError:
                    raise ValueError(f"O campo '{c.rotulo}' deve ser uma data/hora válida.")

        else:
            valor = (form.get(c.nome_chave) or "").strip()
            if valor == "":
                valor = None

        if c.obrigatorio:
            vazio = (
                valor is None
                or valor == ""
                or (c.tipo == "checkbox" and valor is False)
                or (isinstance(valor, list) and len(valor) == 0)
            )
            if vazio:
                raise ValueError(f"O campo '{c.rotulo}' é obrigatório.")

        dados[c.nome_chave] = valor

    return dados


def processar_data_atendimento(form):
    """
    Processa a data principal do atendimento.
    """
    data_atendimento_str = (form.get("data_atendimento") or "").strip()

    if not data_atendimento_str:
        raise ValueError("A data do atendimento é obrigatória.")

    try:
        return datetime.strptime(data_atendimento_str, "%Y-%m-%d").date()
    except ValueError:
        raise ValueError("Data de atendimento inválida.")


def processar_imagens_atendimento(arquivos_imagens, atendimento_id):
    """
    Processa upload das imagens vinculadas ao atendimento.
    """
    erros = []

    for arquivo in arquivos_imagens:
        if not arquivo or not arquivo.filename:
            continue

        if not arquivo_imagem_permitido(arquivo.filename):
            erros.append(f"Arquivo '{arquivo.filename}' não é uma imagem permitida.")
            continue

        caminho_relativo = salvar_imagem_atendimento(arquivo, atendimento_id)
        if not caminho_relativo:
            continue

        imagem = AtendimentoImagem(
            atendimento_id=atendimento_id,
            nome_arquivo=arquivo.filename,
            caminho_arquivo=caminho_relativo,
        )
        db.session.add(imagem)

    return erros