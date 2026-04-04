from __future__ import annotations

from datetime import datetime
import uuid

from werkzeug.security import generate_password_hash, check_password_hash

from . import db


# =========================
# CLIENTE (SaaS)
# =========================
class Cliente(db.Model):
    __tablename__ = "clientes"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(150), nullable=False)
    nome_fantasia = db.Column(db.String(150), nullable=True)
    documento = db.Column(db.String(30), nullable=True, unique=True)
    email = db.Column(db.String(150), nullable=True)
    telefone = db.Column(db.String(30), nullable=True)
    ativo = db.Column(db.Boolean, default=True, nullable=False)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    observacoes = db.Column(db.Text, nullable=True)

    usuarios = db.relationship(
        "Usuario",
        backref=db.backref("cliente", lazy=True),
        lazy=True,
    )

    propriedades = db.relationship(
        "Propriedade",
        backref=db.backref("cliente", lazy=True),
        lazy=True,
    )

    formularios = db.relationship(
        "Formulario",
        backref=db.backref("cliente", lazy=True),
        lazy=True,
        foreign_keys="Formulario.cliente_id",
    )

    def __repr__(self) -> str:
        return f"<Cliente {self.id} {self.nome}>"


# =========================
# USUÁRIO
# =========================
class Usuario(db.Model):
    __tablename__ = "usuarios"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    senha_hash = db.Column(db.String(255), nullable=False)

    # Perfis possíveis:
    # admin_master, admin_cliente, tecnico, veterinario
    perfil = db.Column(db.String(30), nullable=False)

    # admin_master pode existir sem cliente_id
    cliente_id = db.Column(
        db.Integer,
        db.ForeignKey("clientes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    criado_por_id = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    criado_por = db.relationship(
        "Usuario",
        remote_side=[id],
        backref=db.backref("usuarios_criados", lazy=True),
    )

    ativo = db.Column(db.Boolean, default=True, nullable=False)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def set_password(self, senha: str) -> None:
        self.senha_hash = generate_password_hash(senha)

    def check_password(self, senha: str) -> bool:
        return check_password_hash(self.senha_hash, senha)

    def __repr__(self) -> str:
        return (
            f"<Usuario {self.id} {self.email} ({self.perfil}) "
            f"cliente={self.cliente_id} criado_por={self.criado_por_id}>"
        )


# =========================
# PROPRIEDADE
# =========================
class Propriedade(db.Model):
    __tablename__ = "propriedades"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(150), nullable=False)
    produtor = db.Column(db.String(150), nullable=False)
    cidade = db.Column(db.String(100), nullable=True)
    estado = db.Column(db.String(50), nullable=True)

    cliente_id = db.Column(
        db.Integer,
        db.ForeignKey("clientes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    criado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self) -> str:
        return f"<Propriedade {self.id} {self.nome} cliente={self.cliente_id}>"


# =========================
# VÍNCULO USUÁRIO-PROPRIEDADE
# =========================
class UsuarioPropriedade(db.Model):
    __tablename__ = "usuarios_propriedades"

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id", ondelete="CASCADE"),
        nullable=False,
    )
    propriedade_id = db.Column(
        db.Integer,
        db.ForeignKey("propriedades.id", ondelete="CASCADE"),
        nullable=False,
    )

    usuario = db.relationship(
        "Usuario",
        backref=db.backref("vinculos", lazy=True, cascade="all, delete-orphan"),
    )
    propriedade = db.relationship(
        "Propriedade",
        backref=db.backref("usuarios_vinculados", lazy=True, cascade="all, delete-orphan"),
    )

    __table_args__ = (
        db.UniqueConstraint("usuario_id", "propriedade_id", name="uq_usuario_propriedade"),
    )

    def __repr__(self) -> str:
        return f"<UsuarioPropriedade usuario={self.usuario_id} prop={self.propriedade_id}>"


# =========================
# ANIMAL
# =========================
class Animal(db.Model):
    __tablename__ = "animais"

    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(50), nullable=False)
    especie = db.Column(db.String(30), nullable=False, default="bovino")
    nome = db.Column(db.String(100), nullable=True)
    data_nascimento = db.Column(db.Date, nullable=True)
    raca = db.Column(db.String(100), nullable=True)
    sexo = db.Column(db.String(20), nullable=True)
    perfil_genetico = db.Column(db.String(200), nullable=True)

    propriedade_id = db.Column(
        db.Integer,
        db.ForeignKey("propriedades.id"),
        nullable=False,
    )

    propriedade = db.relationship(
        "Propriedade",
        backref=db.backref("animais", lazy=True),
    )

    __table_args__ = (
        db.UniqueConstraint("propriedade_id", "codigo", name="uq_animais_propriedade_codigo"),
    )

    def __repr__(self) -> str:
        return f"<Animal {self.id} {self.codigo} prop={self.propriedade_id}>"


# =========================
# FORMULÁRIO
# =========================
class Formulario(db.Model):
    __tablename__ = "formularios"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    perfil_alvo = db.Column(db.String(20), nullable=False, default="tecnico")
    ativo = db.Column(db.Boolean, default=True, nullable=False)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # NOVOS CAMPOS
    # rural | clinica | hospital
    tipo_contexto = db.Column(db.String(30), nullable=False, default="rural", index=True)

    # True para modelos protegidos do sistema
    template_base = db.Column(db.Boolean, default=False, nullable=False, index=True)

    # formulário personalizado do cliente
    cliente_id = db.Column(
        db.Integer,
        db.ForeignKey("clientes.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # referência ao template original
    formulario_origem_id = db.Column(
        db.Integer,
        db.ForeignKey("formularios.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    formulario_origem = db.relationship(
        "Formulario",
        remote_side=[id],
        backref=db.backref("copias_personalizadas", lazy=True),
        foreign_keys=[formulario_origem_id],
    )

    __table_args__ = (
        db.CheckConstraint(
            "tipo_contexto IN ('rural', 'clinica', 'hospital')",
            name="ck_formulario_tipo_contexto",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<Formulario {self.id} {self.nome} "
            f"contexto={self.tipo_contexto} "
            f"template_base={self.template_base} "
            f"cliente={self.cliente_id}>"
        )


# =========================
# CAMPOS DO FORMULÁRIO
# =========================
class CampoFormulario(db.Model):
    __tablename__ = "campos_formulario"

    id = db.Column(db.Integer, primary_key=True)

    formulario_id = db.Column(
        db.Integer,
        db.ForeignKey("formularios.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    rotulo = db.Column(db.String(120), nullable=False)
    nome_chave = db.Column(db.String(80), nullable=False)
    tipo = db.Column(db.String(20), nullable=False, default="text")
    obrigatorio = db.Column(db.Boolean, default=False, nullable=False)
    opcoes = db.Column(db.JSON, nullable=True)
    ordem = db.Column(db.Integer, default=0, nullable=False)

    # NOVOS CAMPOS
    grupo = db.Column(db.String(80), nullable=True)           # ex.: Identificação, Diagnóstico
    ajuda = db.Column(db.String(255), nullable=True)          # dica breve abaixo do campo
    placeholder = db.Column(db.String(120), nullable=True)    # placeholder do input
    visivel = db.Column(db.Boolean, default=True, nullable=False)
    editavel = db.Column(db.Boolean, default=True, nullable=False)

    formulario = db.relationship(
        "Formulario",
        backref=db.backref("campos", lazy=True, cascade="all, delete-orphan"),
    )

    __table_args__ = (
        db.UniqueConstraint("formulario_id", "nome_chave", name="uq_formulario_nome_chave"),
    )

    def __repr__(self) -> str:
        return (
            f"<CampoFormulario {self.id} {self.nome_chave} ({self.tipo}) "
            f"grupo={self.grupo} editavel={self.editavel}>"
        )


# =========================
# ATENDIMENTO
# =========================
class Atendimento(db.Model):
    __tablename__ = "atendimentos"

    id = db.Column(db.Integer, primary_key=True)

    animal_id = db.Column(
        db.Integer,
        db.ForeignKey("animais.id"),
        nullable=False,
    )

    tecnico_id = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id"),
        nullable=False,
    )

    formulario_id = db.Column(
        db.Integer,
        db.ForeignKey("formularios.id"),
        nullable=True,
    )

    data_atendimento = db.Column(db.Date, nullable=True)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    bloqueado_em = db.Column(db.DateTime, nullable=True)
    dados = db.Column(db.JSON, nullable=False)

    animal = db.relationship(
        "Animal",
        backref=db.backref("atendimentos", lazy=True),
    )
    tecnico = db.relationship(
        "Usuario",
        backref=db.backref("atendimentos_realizados", lazy=True),
    )
    formulario = db.relationship(
        "Formulario",
        backref=db.backref("atendimentos", lazy=True),
    )

    def __repr__(self) -> str:
        return f"<Atendimento {self.id} animal={self.animal_id}>"


# =========================
# ENVIO / TOKENS
# =========================
class Envio(db.Model):
    __tablename__ = "envios"

    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(100), unique=True, default=lambda: str(uuid.uuid4()))
    criado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


# =========================
# CONFIGURAÇÃO GLOBAL DO SISTEMA
# =========================
class ConfiguracaoSistema(db.Model):
    __tablename__ = "configuracao_sistema"

    id = db.Column(db.Integer, primary_key=True)
    nome_plataforma = db.Column(db.String(120))
    subtitulo = db.Column(db.String(200))
    texto_banner = db.Column(db.Text)
    aviso_sanitario = db.Column(db.Text)
    rodape = db.Column(db.Text)
    logo = db.Column(db.String(200))


# =========================
# IMAGENS DO ATENDIMENTO
# =========================
class AtendimentoImagem(db.Model):
    __tablename__ = "atendimentos_imagens"

    id = db.Column(db.Integer, primary_key=True)
    atendimento_id = db.Column(
        db.Integer,
        db.ForeignKey("atendimentos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    nome_arquivo = db.Column(db.String(255), nullable=False)
    caminho_arquivo = db.Column(db.String(500), nullable=False)
    descricao = db.Column(db.String(255), nullable=True)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    atendimento = db.relationship(
        "Atendimento",
        backref=db.backref("imagens", lazy=True, cascade="all, delete-orphan"),
    )

    def __repr__(self) -> str:
        return f"<AtendimentoImagem {self.id} atendimento={self.atendimento_id}>"


# =========================
# EXAMES
# =========================
class Exame(db.Model):
    __tablename__ = "exames"

    id = db.Column(db.Integer, primary_key=True)
    atendimento_id = db.Column(
        db.Integer,
        db.ForeignKey("atendimentos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    categoria = db.Column(db.String(30), nullable=False)  # laboratorial ou imagem
    nome_exame = db.Column(db.String(150), nullable=False)
    data_exame = db.Column(db.Date, nullable=True)
    resultado = db.Column(db.Text, nullable=True)
    observacoes = db.Column(db.Text, nullable=True)
    arquivo = db.Column(db.String(500), nullable=True)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    atendimento = db.relationship(
        "Atendimento",
        backref=db.backref("exames", lazy=True, cascade="all, delete-orphan"),
    )

    def __repr__(self) -> str:
        return f"<Exame {self.id} atendimento={self.atendimento_id} categoria={self.categoria}>"