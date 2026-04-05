from flask import flash, redirect, render_template, request, url_for

from .base import main
from .. import db
from ..helpers.decorators import admin_obrigatorio
from ..models import ConfiguracaoSistema


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
        config.logo = (request.form.get("logo") or "").strip() or None

        db.session.commit()
        flash("Configurações da landing atualizadas com sucesso.", "success")
        return redirect(url_for("main.admin_configuracoes"))

    return render_template("admin_configuracoes.html", config=config)