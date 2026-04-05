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

    usuarios = db.relationship("Usuario", backref=db.backref("cliente", lazy=True), lazy=True)
    propriedades = db.relationship("Propriedade", backref=db.backref("cliente", lazy=True), lazy=True)
    formularios = db.relationship(
        "Formulario",
        backref=db.backref("cliente", lazy=True),
        lazy=True,
        foreign_keys="Formulario.cliente_id",
    )

    def __repr__(self):
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

    perfil = db.Column(db.String(30), nullable=False)

    cliente_id = db.Column(db.Integer, db.ForeignKey("clientes.id", ondelete="SET NULL"), nullable=True, index=True)

    criado_por_id = db.Column(db.Integer, db.ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True, index=True)

    criado_por = db.relationship("Usuario", remote_side=[id], backref=db.backref("usuarios_criados", lazy=True))

    ativo = db.Column(db.Boolean, default=True, nullable=False)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def set_password(self, senha):
        self.senha_hash = generate_password_hash(senha)

    def check_password(self, senha):
        return check_password_hash(self.senha_hash, senha)


# =========================
# PROPRIEDADE
# =========================
class Propriedade(db.Model):
    __tablename__ = "propriedades"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(150), nullable=False)
    produtor = db.Column(db.String(150), nullable=False)
    cidade = db.Column(db.String(100))
    estado = db.Column(db.String(50))

    cliente_id = db.Column(db.Integer, db.ForeignKey("clientes.id", ondelete="CASCADE"), nullable=False, index=True)

    criado_em = db.Column(db.DateTime, default=datetime.utcnow)


# =========================
# VÍNCULO USUÁRIO-PROPRIEDADE
# =========================
class UsuarioPropriedade(db.Model):
    __tablename__ = "usuarios_propriedades"

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id", ondelete="CASCADE"))
    propriedade_id = db.Column(db.Integer, db.ForeignKey("propriedades.id", ondelete="CASCADE"))

    __table_args__ = (
        db.UniqueConstraint("usuario_id", "propriedade_id"),
    )


# =========================
# ANIMAL
# =========================
class Animal(db.Model):
    __tablename__ = "animais"

    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(50), nullable=False)
    especie = db.Column(db.String(30), default="bovino")
    nome = db.Column(db.String(100))
    data_nascimento = db.Column(db.Date)
    raca = db.Column(db.String(100))
    sexo = db.Column(db.String(20))
    perfil_genetico = db.Column(db.String(200))

    propriedade_id = db.Column(db.Integer, db.ForeignKey("propriedades.id"), nullable=False)

    __table_args__ = (
        db.UniqueConstraint("propriedade_id", "codigo"),
    )


# =========================
# FORMULÁRIO
# =========================
class Formulario(db.Model):
    __tablename__ = "formularios"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    perfil_alvo = db.Column(db.String(20), default="tecnico")
    ativo = db.Column(db.Boolean, default=True)

    tipo_contexto = db.Column(db.String(30), default="rural", index=True)
    template_base = db.Column(db.Boolean, default=False, index=True)

    cliente_id = db.Column(db.Integer, db.ForeignKey("clientes.id"), index=True)
    formulario_origem_id = db.Column(db.Integer, db.ForeignKey("formularios.id"))

    criado_em = db.Column(db.DateTime, default=datetime.utcnow)


# =========================
# CAMPOS DO FORMULÁRIO
# =========================
class CampoFormulario(db.Model):
    __tablename__ = "campos_formulario"

    id = db.Column(db.Integer, primary_key=True)
    formulario_id = db.Column(db.Integer, db.ForeignKey("formularios.id"))

    rotulo = db.Column(db.String(120))
    nome_chave = db.Column(db.String(80))
    tipo = db.Column(db.String(20), default="text")
    obrigatorio = db.Column(db.Boolean, default=False)
    opcoes = db.Column(db.JSON)
    ordem = db.Column(db.Integer, default=0)

    grupo = db.Column(db.String(80))
    ajuda = db.Column(db.String(255))
    placeholder = db.Column(db.String(120))

    visivel = db.Column(db.Boolean, default=True)
    editavel = db.Column(db.Boolean, default=True)


# =========================
# ATENDIMENTO
# =========================
class Atendimento(db.Model):
    __tablename__ = "atendimentos"

    id = db.Column(db.Integer, primary_key=True)

    animal_id = db.Column(db.Integer, db.ForeignKey("animais.id"))
    tecnico_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"))
    formulario_id = db.Column(db.Integer, db.ForeignKey("formularios.id"))

    data_atendimento = db.Column(db.Date)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    dados = db.Column(db.JSON)


# =========================
# CONFIGURAÇÃO DO SISTEMA (ATUALIZADA)
# =========================
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


# =========================
# IMAGENS DO ATENDIMENTO
# =========================
class AtendimentoImagem(db.Model):
    __tablename__ = "atendimentos_imagens"

    id = db.Column(db.Integer, primary_key=True)
    atendimento_id = db.Column(db.Integer, db.ForeignKey("atendimentos.id"))
    nome_arquivo = db.Column(db.String(255))
    caminho_arquivo = db.Column(db.String(500))


# =========================
# EXAMES (MANTIDO PARA NÃO QUEBRAR)
# =========================
class Exame(db.Model):
    __tablename__ = "exames"

    id = db.Column(db.Integer, primary_key=True)
    atendimento_id = db.Column(db.Integer, db.ForeignKey("atendimentos.id"))

    categoria = db.Column(db.String(30))
    nome_exame = db.Column(db.String(150))
    data_exame = db.Column(db.Date)
    resultado = db.Column(db.Text)
    observacoes = db.Column(db.Text)
    arquivo = db.Column(db.String(500))