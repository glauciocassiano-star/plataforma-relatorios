from flask import session
from app import db
from app.models import Usuario


def obter_usuario_logado():
    usuario_id = session.get("usuario_id")

    if not usuario_id:
        return None

    usuario = db.session.get(Usuario, usuario_id)

    if not usuario or not usuario.ativo:
        session.clear()
        return None

    return usuario