from ..models import UsuarioPropriedade


def usuario_tem_acesso_propriedade(usuario, propriedade_id):
    if usuario.perfil == "admin":
        return True

    vinculo = UsuarioPropriedade.query.filter_by(
        usuario_id=usuario.id,
        propriedade_id=propriedade_id,
    ).first()

    return vinculo is not None


def usuario_tem_acesso_animal(usuario, animal):
    if usuario.perfil == "admin":
        return True

    vinculo = UsuarioPropriedade.query.filter_by(
        usuario_id=usuario.id,
        propriedade_id=animal.propriedade_id,
    ).first()

    return vinculo is not None