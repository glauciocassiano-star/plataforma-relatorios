from ..models import UsuarioPropriedade


def usuario_eh_admin_master(usuario):
    return usuario is not None and usuario.perfil == "admin_master"


def usuario_eh_admin_cliente(usuario):
    return usuario is not None and usuario.perfil == "admin_cliente"


def usuario_tem_mesmo_cliente(usuario, cliente_id):
    if not usuario:
        return False

    if usuario_eh_admin_master(usuario):
        return True

    return usuario.cliente_id == cliente_id


def usuario_tem_vinculo_propriedade(usuario, propriedade_id):
    if not usuario:
        return False

    if usuario_eh_admin_master(usuario):
        return True

    vinculo = UsuarioPropriedade.query.filter_by(
        usuario_id=usuario.id,
        propriedade_id=propriedade_id,
    ).first()

    return vinculo is not None


def usuario_tem_acesso_propriedade(usuario, propriedade):
    if not usuario or not propriedade:
        return False

    if usuario_eh_admin_master(usuario):
        return True

    if usuario.cliente_id != propriedade.cliente_id:
        return False

    return usuario_tem_vinculo_propriedade(usuario, propriedade.id)


def usuario_tem_acesso_animal(usuario, animal):
    if not usuario or not animal or not animal.propriedade:
        return False

    return usuario_tem_acesso_propriedade(usuario, animal.propriedade)


def usuario_pode_ver_usuario(usuario_logado, usuario_alvo):
    if not usuario_logado or not usuario_alvo:
        return False

    if usuario_eh_admin_master(usuario_logado):
        return True

    if not usuario_eh_admin_cliente(usuario_logado):
        return False

    if usuario_alvo.cliente_id != usuario_logado.cliente_id:
        return False

    if usuario_alvo.perfil not in ["tecnico", "veterinario"]:
        return False

    return usuario_alvo.criado_por_id == usuario_logado.id


def usuario_pode_editar_usuario(usuario_logado, usuario_alvo):
    return usuario_pode_ver_usuario(usuario_logado, usuario_alvo)


def usuario_pode_excluir_usuario(usuario_logado, usuario_alvo):
    if not usuario_logado or not usuario_alvo:
        return False

    if usuario_logado.id == usuario_alvo.id:
        return False

    return usuario_pode_ver_usuario(usuario_logado, usuario_alvo)


def usuario_pode_gerenciar_propriedades_usuario(usuario_logado, usuario_alvo):
    return usuario_pode_ver_usuario(usuario_logado, usuario_alvo)