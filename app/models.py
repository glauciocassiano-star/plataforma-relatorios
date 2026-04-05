from datetime import datetime
from app import db


# ===============================
# USUÁRIO
# ===============================
class Usuario(db.Model):
    __tablename__ = "usuarios"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    senha_hash = db.Column(db.String(255), nullable=False)

    perfil = db.Column(db.String(50), nullable=False)  # admin_master, admin_cliente, tecnico, veterinario

    cliente_id = db.Column(db.Integer, db.ForeignKey("clientes.id"), nullable=True)
    criado_por_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=True)

    ativo = db.Column(db.Boolean, default=True)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)

    cliente = db.relationship("Cliente", backref="usuarios")


# ===============================
# CLIENTE
# ===============================
class Cliente(db.Model):
    __tablename__ = "clientes"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)

    ativo = db.Column(db.Boolean, default=True)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)


# ===============================
# PROPRIEDADE
# ===============================
class Propriedade(db.Model):
    __tablename__ = "propriedades"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)

    cliente_id = db.Column(db.Integer, db.ForeignKey("clientes.id"), nullable=False)

    cidade = db.Column(db.String(120), nullable=True)
    estado = db.Column(db.String(10), nullable=True)

    criado_em = db.Column(db.DateTime, default=datetime.utcnow)

    cliente = db.relationship("Cliente", backref="propriedades")


# ===============================
# VÍNCULO USUÁRIO - PROPRIEDADE
# ===============================
class UsuarioPropriedade(db.Model):
    __tablename__ = "usuarios_propriedades"

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"))
    propriedade_id = db.Column(db.Integer, db.ForeignKey("propriedades.id"))


# ===============================
# ANIMAL
# ===============================
class Animal(db.Model):
    __tablename__ = "animais"

    id = db.Column(db.Integer, primary_key=True)

    codigo = db.Column(db.String(50), nullable=False)
    nome = db.Column(db.String(120), nullable=True)
    especie = db.Column(db.String(50), default="bovino")

    data_nascimento = db.Column(db.Date, nullable=True)
    raca = db.Column(db.String(100), nullable=True)
    sexo = db.Column(db.String(20), nullable=True)

    perfil_genetico = db.Column(db.String(120), nullable=True)

    propriedade_id = db.Column(db.Integer, db.ForeignKey("propriedades.id"), nullable=False)

    propriedade = db.relationship("Propriedade", backref="animais")

    __table_args__ = (
        db.UniqueConstraint("propriedade_id", "codigo", name="uq_animais_propriedade_codigo"),
    )


# ===============================
# FORMULÁRIO
# ===============================
class Formulario(db.Model):
    __tablename__ = "formularios"

    id = db.Column(db.Integer, primary_key=True)

    nome = db.Column(db.String(120), nullable=False)
    perfil_alvo = db.Column(db.String(50), nullable=False)

    tipo_contexto = db.Column(db.String(50), default="rural")

    ativo = db.Column(db.Boolean, default=True)

    template_base = db.Column(db.Boolean, default=False)

    cliente_id = db.Column(db.Integer, db.ForeignKey("clientes.id"), nullable=True)

    formulario_origem_id = db.Column(db.Integer, db.ForeignKey("formularios.id"), nullable=True)

    criado_em = db.Column(db.DateTime, default=datetime.utcnow)

    cliente = db.relationship("Cliente", backref="formularios")


# ===============================
# CAMPOS DO FORMULÁRIO
# ===============================
class CampoFormulario(db.Model):
    __tablename__ = "campos_formulario"

    id = db.Column(db.Integer, primary_key=True)

    formulario_id = db.Column(db.Integer, db.ForeignKey("formularios.id"), nullable=False)

    rotulo = db.Column(db.String(120), nullable=False)
    nome_chave = db.Column(db.String(120), nullable=False)

    tipo = db.Column(db.String(50), default="text")

    obrigatorio = db.Column(db.Boolean, default=False)

    opcoes = db.Column(db.JSON, nullable=True)

    ordem = db.Column(db.Integer, default=0)

    # Novos campos (UX avançada)
    grupo = db.Column(db.String(120), nullable=True)
    ajuda = db.Column(db.String(255), nullable=True)
    placeholder = db.Column(db.String(255), nullable=True)

    visivel = db.Column(db.Boolean, default=True)
    editavel = db.Column(db.Boolean, default=True)


# ===============================
# ATENDIMENTO
# ===============================
class Atendimento(db.Model):
    __tablename__ = "atendimentos"

    id = db.Column(db.Integer, primary_key=True)

    animal_id = db.Column(db.Integer, db.ForeignKey("animais.id"), nullable=False)
    tecnico_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)

    formulario_id = db.Column(db.Integer, db.ForeignKey("formularios.id"), nullable=True)

    data_atendimento = db.Column(db.Date, nullable=False)

    dados = db.Column(db.JSON, nullable=True)

    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    bloqueado_em = db.Column(db.DateTime, nullable=True)

    animal = db.relationship("Animal", backref="atendimentos")


# ===============================
# CONFIGURAÇÃO DO SISTEMA (LANDING)
# ===============================
class ConfiguracaoSistema(db.Model):
    __tablename__ = "configuracao_sistema"

    id = db.Column(db.Integer, primary_key=True)

    # Identidade
    nome_plataforma = db.Column(db.String(120), nullable=True)
    subtitulo = db.Column(db.String(200), nullable=True)

    # Banner
    titulo_banner = db.Column(db.String(200), nullable=True)
    texto_banner = db.Column(db.Text, nullable=True)
    aviso_sanitario = db.Column(db.Text, nullable=True)

    # Botões
    botao_principal_texto = db.Column(db.String(80), nullable=True)
    botao_principal_link = db.Column(db.String(200), nullable=True)

    botao_secundario_texto = db.Column(db.String(80), nullable=True)
    botao_secundario_link = db.Column(db.String(200), nullable=True)

    # Visual
    logo = db.Column(db.String(200), nullable=True)

    # Rodapé
    rodape = db.Column(db.Text, nullable=True)