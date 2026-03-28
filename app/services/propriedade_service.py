from app.models import Propriedade, UsuarioPropriedade


def listar_propriedades_do_usuario(usuario):
    if not usuario:
        return []

    if usuario.perfil == "admin_master":
        return (
            Propriedade.query
            .order_by(Propriedade.id.desc())
            .all()
        )

    return (
        Propriedade.query
        .join(
            UsuarioPropriedade,
            UsuarioPropriedade.propriedade_id == Propriedade.id
        )
        .filter(
            UsuarioPropriedade.usuario_id == usuario.id,
            Propriedade.cliente_id == usuario.cliente_id
        )
        .order_by(Propriedade.id.desc())
        .all()
    )