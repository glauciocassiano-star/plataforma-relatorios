import os
import uuid

from flask import current_app

ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}


def arquivo_imagem_permitido(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS


def salvar_imagem_atendimento(arquivo, atendimento_id: int) -> str | None:
    if not arquivo or not arquivo.filename:
        return None

    if not arquivo_imagem_permitido(arquivo.filename):
        return None

    extensao = arquivo.filename.rsplit(".", 1)[1].lower()
    nome_final = f"{atendimento_id}_{uuid.uuid4().hex}.{extensao}"

    pasta_destino = os.path.join(
        current_app.config["UPLOAD_FOLDER"],
        "atendimentos",
        str(atendimento_id),
    )

    os.makedirs(pasta_destino, exist_ok=True)

    caminho_absoluto = os.path.join(pasta_destino, nome_final)
    arquivo.save(caminho_absoluto)

    caminho_relativo = os.path.join(
        "uploads",
        "atendimentos",
        str(atendimento_id),
        nome_final,
    ).replace("\\", "/")

    return caminho_relativo

ALLOWED_EXAM_EXTENSIONS = {"pdf", "png", "jpg", "jpeg", "webp"}


def arquivo_exame_permitido(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXAM_EXTENSIONS

def salvar_arquivo_exame(arquivo, atendimento_id: int) -> str | None:
    if not arquivo or not arquivo.filename:
        return None

    if not arquivo_exame_permitido(arquivo.filename):
        return None

    extensao = arquivo.filename.rsplit(".", 1)[1].lower()
    nome_final = f"exame_{atendimento_id}_{uuid.uuid4().hex}.{extensao}"

    pasta_destino = os.path.join(
        current_app.config["UPLOAD_FOLDER"],
        "exames",
        str(atendimento_id),
    )
    os.makedirs(pasta_destino, exist_ok=True)

    caminho_absoluto = os.path.join(pasta_destino, nome_final)
    arquivo.save(caminho_absoluto)

    caminho_relativo = os.path.join(
        "uploads",
        "exames",
        str(atendimento_id),
        nome_final,
    ).replace("\\", "/")

    return caminho_relativo