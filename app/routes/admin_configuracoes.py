import os

from flask import current_app, flash, redirect, render_template, request, url_for
from werkzeug.utils import secure_filename

from .base import main
from .. import db
from ..helpers.decorators import admin_obrigatorio
from ..models import ConfiguracaoSistema


EXTENSOES_LOGO_PERMITIDAS = {"png", "jpg", "jpeg", "webp", "svg"}


def arquivo_logo_permitido(nome_arquivo):
    if not nome_arquivo or "." not in nome_arquivo:
        return False
    extensao = nome_arquivo.rsplit(".", 1)[1].lower()
    return extensao in EXTENSOES_LOGO_PERMITIDAS


@main.route("/admin/configuracoes", methods=["GET", "POST"])
@admin_obrigatorio
def admin_configuracoes():
    config = ConfiguracaoSistema.query.first()

    if not config:
        config = ConfiguracaoSistema()
        db.session.add(config)
        db.session.commit()

    if request.method == "POST":
        config.nome_plataforma = (request.form.get("nome_plataforma") or "").strip() or None
        config.subtitulo = (request.form.get("subtitulo") or "").strip() or None

        config.titulo_banner = (request.form.get("titulo_banner") or "").strip() or None
        config.texto_banner = (request.form.get("texto_banner") or "").strip() or None
        config.aviso_sanitario = (request.form.get("aviso_sanitario") or "").strip() or None

        config.botao_principal_texto = (request.form.get("botao_principal_texto") or "").strip() or None
        config.botao_principal_link = (request.form.get("botao_principal_link") or "").strip() or None

        config.botao_secundario_texto = (request.form.get("botao_secundario_texto") or "").strip() or None
        config.botao_secundario_link = (request.form.get("botao_secundario_link") or "").strip() or None

        config.rodape = (request.form.get("rodape") or "").strip() or None

        arquivo_logo = request.files.get("logo")

        if arquivo_logo and arquivo_logo.filename:
            if not arquivo_logo_permitido(arquivo_logo.filename):
                flash("Formato de logo inválido. Use PNG, JPG, JPEG, WEBP ou SVG.", "error")
                return redirect(url_for("main.admin_configuracoes"))

            nome_seguro = secure_filename(arquivo_logo.filename)

            pasta_upload = os.path.join(current_app.static_folder, "uploads", "config")
            os.makedirs(pasta_upload, exist_ok=True)

            caminho_completo = os.path.join(pasta_upload, nome_seguro)
            arquivo_logo.save(caminho_completo)

            config.logo = f"/static/uploads/config/{nome_seguro}"

        db.session.commit()
        flash("Configurações da landing atualizadas com sucesso.", "success")
        return redirect(url_for("main.admin_configuracoes"))

    return render_template("admin_configuracoes.html", config=config)
