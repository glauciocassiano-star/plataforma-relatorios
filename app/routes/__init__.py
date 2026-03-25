from .base import main

# Core
from . import auth
from . import dashboard
from . import propriedades
from . import animais
from . import atendimentos
from . import relatorios
from . import sync

# Admin
from . import admin_formularios
from . import admin_usuarios
from . import admin_configuracoes
from . import admin_backup
from . import admin_painel

__all__ = ["main"]