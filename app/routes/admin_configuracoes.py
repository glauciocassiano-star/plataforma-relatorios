import os

from flask import flash, redirect, render_template, request, url_for
from werkzeug.utils import secure_filename

from .base import main
from .. import db
from ..helpers.decorators import login_obrigatorio, admin_obrigatorio
from ..models import ConfiguracaoSistema


@main.route("/admin/configuracoes", methods=["GET", "POST"])
@login_obrigatorio
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
        config.texto_banner = (request.form.get("texto_banner") or "").strip() or None
        config.aviso_sanitario = (request.form.get("aviso_sanitario") or "").strip() or None
        config.rodape = (request.form.get("rodape") or "").strip() or None

        arquivo_logo = request.files.get("logo")

        if arquivo_logo and arquivo_logo.filename:
            extensoes_permitidas = {"png", "jpg", "jpeg", "webp"}
            nome_original = secure_filename(arquivo_logo.filename)
            extensao = nome_original.rsplit(".", 1)[-1].lower() if "." in nome_original else ""

            if extensao not in extensoes_permitidas:
                flash("Formato de logo inválido. Envie PNG, JPG, JPEG ou WEBP.", "error")
                return redirect(url_for("main.admin_configuracoes"))

            pasta_logo = os.path.join("app", "static", "uploads", "logo")
            os.makedirs(pasta_logo, exist_ok=True)

            nome_arquivo = f"logo_sistema.{extensao}"
            caminho_absoluto = os.path.join(pasta_logo, nome_arquivo)
            arquivo_logo.save(caminho_absoluto)

            config.logo = f"uploads/logo/{nome_arquivo}"

        db.session.commit()

        flash("Configurações atualizadas.", "success")
        return redirect(url_for("main.admin_configuracoes"))

    return render_template("admin_configuracoes.html", config=config)