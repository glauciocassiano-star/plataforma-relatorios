from ..models import UsuarioPropriedade


def usuario_ativo(usuario):
    return usuario is not None and getattr(usuario, "ativo", True)


def usuario_eh_admin_master(usuario):
    return usuario_ativo(usuario) and usuario.perfil == "admin_master"


def usuario_eh_admin_cliente(usuario):
    return usuario_ativo(usuario) and usuario.perfil == "admin_cliente"


def cliente_ativo(usuario):
    if usuario is None:
        return False

    # admin_master pode existir sem cliente
    if usuario_eh_admin_master(usuario):
        return True

    if not hasattr(usuario, "cliente") or usuario.cliente is None:
        return False

    return getattr(usuario.cliente, "ativo", True)


def usuario_tem_mesmo_cliente(usuario, cliente_id):
    if not usuario_ativo(usuario) or not cliente_ativo(usuario):
        return False

    if usuario_eh_admin_master(usuario):
        return True

    return usuario.cliente_id == cliente_id


def usuario_tem_vinculo_propriedade(usuario, propriedade_id):
    if not usuario_ativo(usuario) or not cliente_ativo(usuario):
        return False

    if usuario_eh_admin_master(usuario):
        return True

    vinculo = UsuarioPropriedade.query.filter_by(
        usuario_id=usuario.id,
        propriedade_id=propriedade_id,
    ).first()

    return vinculo is not None


def usuario_tem_acesso_propriedade(usuario, propriedade):
    if not usuario_ativo(usuario) or not propriedade:
        return False

    if not cliente_ativo(usuario):
        return False

    if usuario_eh_admin_master(usuario):
        return True

    if usuario.cliente_id != propriedade.cliente_id:
        return False

    # admin_cliente pode acessar todas as propriedades do próprio cliente
    if usuario_eh_admin_cliente(usuario):
        return True

    return usuario_tem_vinculo_propriedade(usuario, propriedade.id)


def usuario_tem_acesso_animal(usuario, animal):
    if not usuario_ativo(usuario) or not animal or not animal.propriedade:
        return False

    if usuario_eh_admin_master(usuario):
        return True

    return usuario_tem_acesso_propriedade(usuario, animal.propriedade)


def usuario_pode_ver_usuario(usuario_logado, usuario_alvo):
    if not usuario_ativo(usuario_logado) or not usuario_ativo(usuario_alvo):
        return False

    if usuario_eh_admin_master(usuario_logado):
        return True

    if not cliente_ativo(usuario_logado):
        return False

    if not usuario_eh_admin_cliente(usuario_logado):
        return False

    if usuario_alvo.cliente_id != usuario_logado.cliente_id:
        return False

    return usuario_alvo.perfil in ["tecnico", "veterinario", "admin_cliente"]


def usuario_pode_editar_usuario(usuario_logado, usuario_alvo):
    if not usuario_ativo(usuario_logado) or not usuario_ativo(usuario_alvo):
        return False

    if usuario_eh_admin_master(usuario_logado):
        return True

    if not usuario_pode_ver_usuario(usuario_logado, usuario_alvo):
        return False

    # admin_cliente não pode editar admin_master
    if usuario_alvo.perfil == "admin_master":
        return False

    return True


def usuario_pode_excluir_usuario(usuario_logado, usuario_alvo):
    if not usuario_ativo(usuario_logado) or not usuario_ativo(usuario_alvo):
        return False

    if usuario_logado.id == usuario_alvo.id:
        return False

    if usuario_eh_admin_master(usuario_logado):
        return True

    return usuario_pode_editar_usuario(usuario_logado, usuario_alvo)


def usuario_pode_gerenciar_propriedades_usuario(usuario_logado, usuario_alvo):
    if not usuario_ativo(usuario_logado) or not usuario_ativo(usuario_alvo):
        return False

    if usuario_eh_admin_master(usuario_logado):
        return True

    return usuario_pode_editar_usuario(usuario_logado, usuario_alvo)