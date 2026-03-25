import os
from flask import Flask, request, redirect, flash
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def create_app():
    app = Flask(__name__)

    BASE_DIR = os.path.abspath(os.path.dirname(__file__))

    # ===============================
    # CONFIGURAÇÕES BÁSICAS
    # ===============================

    app.config["SECRET_KEY"] = "chave-super-secreta-123"

    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(
        BASE_DIR, "..", "instance", "database.db"
    )

    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # ===============================
    # CONFIGURAÇÕES DE UPLOAD
    # ===============================

    app.config["UPLOAD_FOLDER"] = os.path.join(BASE_DIR, "static", "uploads")

    # limite de upload (8 MB)
    app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024

    # cria pasta uploads automaticamente
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # ===============================
    # INICIALIZA BANCO
    # ===============================

    db.init_app(app)

    # importa models para registrar tabelas
    from . import models  # noqa: F401
    from .models import ConfiguracaoSistema

    # ===============================
    # REGISTRA ROTAS
    # ===============================

    from .routes import main
    app.register_blueprint(main)

    # ===============================
    # CONFIGURAÇÃO GLOBAL
    # ===============================

    @app.context_processor
    def inject_configuracao_sistema():
        config = ConfiguracaoSistema.query.first()
        return dict(config_sistema=config)

    # ===============================
    # TRATAMENTO DE ERRO DE UPLOAD
    # ===============================

    @app.errorhandler(413)
    def arquivo_muito_grande(e):
        flash("O arquivo enviado é muito grande. O limite é 8 MB.", "error")
        return redirect(request.url)

    # ===============================
    # CRIA TABELAS
    # ===============================

    with app.app_context():
        db.create_all()

    return app