import os
from flask import Flask, request, redirect, flash, session
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def create_app():
    app = Flask(__name__)

    BASE_DIR = os.path.abspath(os.path.dirname(__file__))

    # ===============================
    # CONFIGURAÇÕES BÁSICAS
    # ===============================

    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-key-local")

    database_url = os.getenv("DATABASE_URL")

    if database_url:
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)

        app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    else:
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
    from .models import ConfiguracaoSistema, Usuario

    # ===============================
    # REGISTRA ROTAS
    # ===============================

    from .routes import main
    app.register_blueprint(main)

    # ===============================
    # CONTEXTO GLOBAL DOS TEMPLATES
    # ===============================

    @app.context_processor
    def inject_global_context():
        config = ConfiguracaoSistema.query.first()

        usuario_logado = None
        usuario_id = session.get("usuario_id")

        if usuario_id:
            usuario_logado = db.session.get(Usuario, usuario_id)

        return dict(
            config_sistema=config,
            usuario_logado=usuario_logado
        )

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