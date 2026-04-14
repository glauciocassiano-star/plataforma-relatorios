from __future__ import annotations

from datetime import datetime

from werkzeug.security import check_password_hash, generate_password_hash

from . import db


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
        back_populates="cliente",
        lazy=True,
        cascade="all, delete-orphan",
    )
    propriedades = db.relationship(
        "Propriedade",
        back_populates="cliente",
        lazy=True,
        cascade="all, delete-orphan",
    )
    formularios = db.relationship(
        "Formulario",
        back_populates="cliente",
        lazy=True,
        foreign_keys="Formulario.cliente_id",
    )
    leituras_sensor = db.relationship(
        "LeituraSensor",
        back_populates="cliente",
        lazy=True,
    )

    def __repr__(self):
        return f"<Cliente {self.id} {self.nome}>"


class Usuario(db.Model):
    __tablename__ = "usuarios"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    senha_hash = db.Column(db.String(255), nullable=False)
    perfil = db.Column(db.String(30), nullable=False)
    pode_usar_sensor = db.Column(db.Boolean, default=False, nullable=False)

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

    ativo = db.Column(db.Boolean, default=True, nullable=False)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    cliente = db.relationship("Cliente", back_populates="usuarios")
    criado_por = db.relationship(
        "Usuario",
        remote_side=[id],
        backref=db.backref("usuarios_criados", lazy=True),
    )
    propriedades_vinculadas = db.relationship(
        "UsuarioPropriedade",
        back_populates="usuario",
        lazy=True,
        cascade="all, delete-orphan",
    )
    atendimentos_registrados = db.relationship(
        "Atendimento",
        back_populates="tecnico",
        lazy=True,
        foreign_keys="Atendimento.tecnico_id",
    )
    leituras_sensor = db.relationship(
        "LeituraSensor",
        back_populates="usuario",
        lazy=True,
        foreign_keys="LeituraSensor.usuario_id",
    )

    def set_password(self, senha):
        self.senha_hash = generate_password_hash(senha)

    def check_password(self, senha):
        return check_password_hash(self.senha_hash, senha)

    def __repr__(self):
        return f"<Usuario {self.id} {self.email}>"


class Propriedade(db.Model):
    __tablename__ = "propriedades"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(150), nullable=False)
    produtor = db.Column(db.String(150), nullable=False)
    cidade = db.Column(db.String(100))
    estado = db.Column(db.String(50))
    criado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    cliente_id = db.Column(
        db.Integer,
        db.ForeignKey("clientes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    cliente = db.relationship("Cliente", back_populates="propriedades")
    animais = db.relationship(
        "Animal",
        back_populates="propriedade",
        lazy=True,
        cascade="all, delete-orphan",
    )
    usuarios_vinculados = db.relationship(
        "UsuarioPropriedade",
        back_populates="propriedade",
        lazy=True,
        cascade="all, delete-orphan",
    )
    leituras_sensor = db.relationship(
        "LeituraSensor",
        back_populates="propriedade",
        lazy=True,
    )

    def __repr__(self):
        return f"<Propriedade {self.id} {self.nome}>"


class UsuarioPropriedade(db.Model):
    __tablename__ = "usuarios_propriedades"

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    propriedade_id = db.Column(
        db.Integer,
        db.ForeignKey("propriedades.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    usuario = db.relationship("Usuario", back_populates="propriedades_vinculadas")
    propriedade = db.relationship("Propriedade", back_populates="usuarios_vinculados")

    __table_args__ = (db.UniqueConstraint("usuario_id", "propriedade_id"),)


class Animal(db.Model):
    __tablename__ = "animais"

    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(50), nullable=False)
    especie = db.Column(db.String(30), default="bovino", nullable=False)
    nome = db.Column(db.String(100))
    data_nascimento = db.Column(db.Date)
    raca = db.Column(db.String(100))
    sexo = db.Column(db.String(20))
    perfil_genetico = db.Column(db.String(200))

    propriedade_id = db.Column(
        db.Integer,
        db.ForeignKey("propriedades.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    propriedade = db.relationship("Propriedade", back_populates="animais")
    atendimentos = db.relationship(
        "Atendimento",
        back_populates="animal",
        lazy=True,
        cascade="all, delete-orphan",
        order_by="desc(Atendimento.data_atendimento), desc(Atendimento.criado_em)",
    )
    leituras_sensor = db.relationship(
        "LeituraSensor",
        back_populates="animal",
        lazy=True,
        cascade="all, delete-orphan",
        order_by="desc(LeituraSensor.criado_em)",
    )

    __table_args__ = (db.UniqueConstraint("propriedade_id", "codigo"),)

    def __repr__(self):
        return f"<Animal {self.id} {self.codigo}>"


class Formulario(db.Model):
    __tablename__ = "formularios"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    perfil_alvo = db.Column(db.String(20), default="tecnico", nullable=False)
    ativo = db.Column(db.Boolean, default=True, nullable=False)
    tipo_contexto = db.Column(db.String(30), default="rural", index=True)
    template_base = db.Column(db.Boolean, default=False, index=True)
    usa_sensor_mastite = db.Column(db.Boolean, default=False, nullable=False)
    sensor_obrigatorio = db.Column(db.Boolean, default=False, nullable=False)

    cliente_id = db.Column(db.Integer, db.ForeignKey("clientes.id"), index=True)
    formulario_origem_id = db.Column(db.Integer, db.ForeignKey("formularios.id"))
    criado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    cliente = db.relationship(
        "Cliente",
        back_populates="formularios",
        foreign_keys=[cliente_id],
    )
    formulario_origem = db.relationship(
        "Formulario",
        remote_side=[id],
        backref=db.backref("formularios_clonados", lazy=True),
    )
    campos = db.relationship(
        "CampoFormulario",
        back_populates="formulario",
        lazy=True,
        cascade="all, delete-orphan",
        order_by="CampoFormulario.ordem.asc(), CampoFormulario.id.asc()",
    )
    atendimentos = db.relationship("Atendimento", back_populates="formulario", lazy=True)

    def __repr__(self):
        return f"<Formulario {self.id} {self.nome}>"


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
    tipo = db.Column(db.String(20), default="text", nullable=False)
    obrigatorio = db.Column(db.Boolean, default=False, nullable=False)
    opcoes = db.Column(db.JSON)
    ordem = db.Column(db.Integer, default=0, nullable=False)

    grupo = db.Column(db.String(80))
    ajuda = db.Column(db.String(255))
    placeholder = db.Column(db.String(120))
    visivel = db.Column(db.Boolean, default=True, nullable=False)
    editavel = db.Column(db.Boolean, default=True, nullable=False)

    formulario = db.relationship("Formulario", back_populates="campos")

    def __repr__(self):
        return f"<CampoFormulario {self.id} {self.nome_chave}>"


class Atendimento(db.Model):
    __tablename__ = "atendimentos"

    id = db.Column(db.Integer, primary_key=True)
    animal_id = db.Column(
        db.Integer,
        db.ForeignKey("animais.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tecnico_id = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    formulario_id = db.Column(
        db.Integer,
        db.ForeignKey("formularios.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    data_atendimento = db.Column(db.Date, nullable=False, index=True)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    bloqueado_em = db.Column(db.DateTime, nullable=True)
    dados = db.Column(db.JSON, default=dict)

    animal = db.relationship("Animal", back_populates="atendimentos")
    tecnico = db.relationship(
        "Usuario",
        back_populates="atendimentos_registrados",
        foreign_keys=[tecnico_id],
    )
    formulario = db.relationship("Formulario", back_populates="atendimentos")
    imagens = db.relationship(
        "AtendimentoImagem",
        back_populates="atendimento",
        lazy=True,
        cascade="all, delete-orphan",
    )
    exames = db.relationship(
        "Exame",
        back_populates="atendimento",
        lazy=True,
        cascade="all, delete-orphan",
        order_by="desc(Exame.data_exame), desc(Exame.id)",
    )
    leituras_sensor = db.relationship(
        "LeituraSensor",
        back_populates="atendimento",
        lazy=True,
        order_by="desc(LeituraSensor.criado_em)",
    )

    def __repr__(self):
        return f"<Atendimento {self.id} animal={self.animal_id}>"


class LeituraSensor(db.Model):
    __tablename__ = "leituras_sensor"

    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(
        db.Integer,
        db.ForeignKey("clientes.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    propriedade_id = db.Column(
        db.Integer,
        db.ForeignKey("propriedades.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    animal_id = db.Column(
        db.Integer,
        db.ForeignKey("animais.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    atendimento_id = db.Column(
        db.Integer,
        db.ForeignKey("atendimentos.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    usuario_id = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    tipo_sensor = db.Column(db.String(80), nullable=False, default="mastite_subclinica")
    biomarcador_principal = db.Column(
        db.String(80),
        nullable=False,
        default="condutividade_eletrica",
    )
    quarto_mamario = db.Column(db.String(20), nullable=True)

    condutividade = db.Column(db.Float, nullable=False)
    temperatura = db.Column(db.Float, nullable=True)
    variacao = db.Column(db.Float, nullable=True)
    consistencia = db.Column(db.Float, nullable=True)
    quantidade_leituras = db.Column(db.Integer, nullable=False, default=1)

    risco_estimado = db.Column(db.Float, nullable=False)
    confianca = db.Column(db.Float, nullable=False)
    intervalo_inferior = db.Column(db.Float, nullable=True)
    intervalo_superior = db.Column(db.Float, nullable=True)

    classificacao = db.Column(db.String(50), nullable=False)
    recomendacao = db.Column(db.String(255), nullable=True)
    status_validacao = db.Column(db.String(30), nullable=False, default="triagem")

    confirmado_laboratorial = db.Column(db.Boolean, default=False, nullable=False)
    data_confirmacao = db.Column(db.Date, nullable=True)

    observacoes = db.Column(db.Text, nullable=True)
    dados_brutos = db.Column(db.JSON, nullable=True)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    atualizado_em = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    cliente = db.relationship("Cliente", back_populates="leituras_sensor")
    propriedade = db.relationship("Propriedade", back_populates="leituras_sensor")
    animal = db.relationship("Animal", back_populates="leituras_sensor")
    atendimento = db.relationship("Atendimento", back_populates="leituras_sensor")
    usuario = db.relationship(
        "Usuario",
        back_populates="leituras_sensor",
        foreign_keys=[usuario_id],
    )

    def __repr__(self):
        return f"<LeituraSensor {self.id} animal={self.animal_id} risco={self.risco_estimado}>"


class ConfiguracaoSistema(db.Model):
    __tablename__ = "configuracao_sistema"

    id = db.Column(db.Integer, primary_key=True)
    nome_plataforma = db.Column(db.String(120))
    subtitulo = db.Column(db.String(200))
    titulo_banner = db.Column(db.String(200))
    texto_banner = db.Column(db.Text)
    aviso_sanitario = db.Column(db.Text)
    botao_principal_texto = db.Column(db.String(80))
    botao_principal_link = db.Column(db.String(200))
    botao_secundario_texto = db.Column(db.String(80))
    botao_secundario_link = db.Column(db.String(200))
    rodape = db.Column(db.Text)
    logo = db.Column(db.String(200))


class AtendimentoImagem(db.Model):
    __tablename__ = "atendimentos_imagens"

    id = db.Column(db.Integer, primary_key=True)
    atendimento_id = db.Column(
        db.Integer,
        db.ForeignKey("atendimentos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    nome_arquivo = db.Column(db.String(255))
    caminho_arquivo = db.Column(db.String(500))

    atendimento = db.relationship("Atendimento", back_populates="imagens")


class Exame(db.Model):
    __tablename__ = "exames"

    id = db.Column(db.Integer, primary_key=True)
    atendimento_id = db.Column(
        db.Integer,
        db.ForeignKey("atendimentos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    categoria = db.Column(db.String(30))
    nome_exame = db.Column(db.String(150), nullable=False)
    data_exame = db.Column(db.Date)
    resultado = db.Column(db.Text)
    observacoes = db.Column(db.Text)
    arquivo = db.Column(db.String(500))

    atendimento = db.relationship("Atendimento", back_populates="exames")
