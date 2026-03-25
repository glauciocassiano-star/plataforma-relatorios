from datetime import datetime

from .. import db
from ..helpers.uploads import arquivo_imagem_permitido, salvar_imagem_atendimento
from ..models import AtendimentoImagem


def processar_dados_formulario(campos, form):
    dados = {}

    for c in campos:
        if c.tipo == "checkbox":
            valor = True if form.get(c.nome_chave) else False
        else:
            valor = (form.get(c.nome_chave) or "").strip()

        if c.obrigatorio and (valor == "" or valor is False):
            raise ValueError(f"O campo '{c.rotulo}' é obrigatório.")

        if c.tipo == "number" and valor != "":
            try:
                valor = float(valor) if "." in str(valor) else int(valor)
            except ValueError:
                raise ValueError(f"'{c.rotulo}' deve ser numérico.")

        if c.tipo == "date" and valor != "":
            try:
                datetime.strptime(valor, "%Y-%m-%d")
            except ValueError:
                raise ValueError(f"'{c.rotulo}' deve ser uma data válida.")

        dados[c.nome_chave] = valor

    return dados


def processar_data_atendimento(form):
    data_atendimento_str = (form.get("data_atendimento") or "").strip()

    if not data_atendimento_str:
        raise ValueError("A data do atendimento é obrigatória.")

    try:
        return datetime.strptime(data_atendimento_str, "%Y-%m-%d").date()
    except ValueError:
        raise ValueError("Data de atendimento inválida.")


def processar_imagens_atendimento(arquivos_imagens, atendimento_id):
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