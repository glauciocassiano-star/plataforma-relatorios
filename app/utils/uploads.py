import os
import uuid

from flask import current_app
from werkzeug.utils import secure_filename


EXTENSOES_IMAGEM_PERMITIDAS = {"png", "jpg", "jpeg", "webp"}
EXTENSOES_EXAME_PERMITIDAS = {
    "pdf", "png", "jpg", "jpeg", "webp", "doc", "docx", "xls", "xlsx"
}


def arquivo_permitido(nome_arquivo, extensoes_permitidas):
    return (
        "." in nome_arquivo
        and nome_arquivo.rsplit(".", 1)[1].lower() in extensoes_permitidas
    )


def salvar_imagem_atendimento(atendimento_id, imagem):
    if not imagem or not imagem.filename:
        return None

    if not arquivo_permitido(imagem.filename, EXTENSOES_IMAGEM_PERMITIDAS):
        return None

    nome_original = secure_filename(imagem.filename)
    extensao = nome_original.rsplit(".", 1)[1].lower()
    nome_final = f"atendimento_{atendimento_id}_{uuid.uuid4().hex}.{extensao}"

    pasta_destino = os.path.join(
        current_app.config["UPLOAD_FOLDER"],
        "atendimentos",
    )
    os.makedirs(pasta_destino, exist_ok=True)

    caminho_absoluto = os.path.join(pasta_destino, nome_final)
    imagem.save(caminho_absoluto)

    caminho_relativo = os.path.join("uploads", "atendimentos", nome_final).replace("\\", "/")

    from app import db
    from app.models import AtendimentoImagem

    nova_imagem = AtendimentoImagem(
        atendimento_id=atendimento_id,
        nome_arquivo=nome_original,
        caminho_arquivo=caminho_relativo,
    )
    db.session.add(nova_imagem)
    db.session.commit()

    return nova_imagem


def salvar_arquivo_exame(arquivo):
    if not arquivo or not arquivo.filename:
        return None

    if not arquivo_permitido(arquivo.filename, EXTENSOES_EXAME_PERMITIDAS):
        return None

    nome_original = secure_filename(arquivo.filename)
    extensao = nome_original.rsplit(".", 1)[1].lower()
    nome_final = f"exame_{uuid.uuid4().hex}.{extensao}"

    pasta_destino = os.path.join(
        current_app.config["UPLOAD_FOLDER"],
        "exames",
    )
    os.makedirs(pasta_destino, exist_ok=True)

    caminho_absoluto = os.path.join(pasta_destino, nome_final)
    arquivo.save(caminho_absoluto)

    caminho_relativo = os.path.join("uploads", "exames", nome_final).replace("\\", "/")
    return caminho_relativo