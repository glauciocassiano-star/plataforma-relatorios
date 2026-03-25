from app import db
from app.models import Propriedade, UsuarioPropriedade


def listar_propriedades_do_usuario(usuario):
    if usuario.perfil == "admin":
        return Propriedade.query.order_by(Propriedade.id.desc()).all()

    return (
        Propriedade.query
        .join(UsuarioPropriedade, UsuarioPropriedade.propriedade_id == Propriedade.id)
        .filter(UsuarioPropriedade.usuario_id == usuario.id)
        .order_by(Propriedade.id.desc())
        .all()
    )