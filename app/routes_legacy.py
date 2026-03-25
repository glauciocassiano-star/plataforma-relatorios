
# app/routes.py

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime

from flask import (
    Blueprint,
    Response,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from weasyprint import HTML
from werkzeug.utils import secure_filename

from . import db
from .helpers.auth import obter_usuario_logado
from .helpers.permissoes import (
    usuario_tem_acesso_animal,
    usuario_tem_acesso_propriedade,
)
from .models import (
    Animal,
    Atendimento,
    AtendimentoImagem,
    CampoFormulario,
    ConfiguracaoSistema,
    Formulario,
    Propriedade,
    Usuario,
    UsuarioPropriedade,
)
from .services.animal_service import (
    criar_animal,
    listar_animais_da_propriedade,
)
from .services.propriedade_service import listar_propriedades_do_usuario

main = Blueprint("main", __name__)

ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

# ==========================
# 🔐 LOGIN
# ==========================
@main.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        senha = request.form.get("senha") or ""

        usuario = Usuario.query.filter_by(email=email).first()

        if usuario and usuario.check_password(senha):
            session["usuario_id"] = usuario.id
            session["perfil"] = usuario.perfil
            return redirect(url_for("main.painel"))

        flash("Email ou senha inválidos.", "error")
        return redirect(url_for("main.login"))

    return render_template("login.html")


# ==========================
# 🚪 LOGOUT
# ==========================
@main.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("main.login"))


# ==========================
# 🏠 PAINEL
# ==========================
@main.route("/")
def painel():
    usuario = obter_usuario_logado()
    if not usuario:
        return redirect(url_for("main.login"))

    propriedades = listar_propriedades_do_usuario(usuario)
    propriedades_ids = [p.id for p in propriedades]

    if usuario.perfil == "admin":
        total_animais = Animal.query.count()
        atendimentos = Atendimento.query.all()
    else:
        total_animais = (
            Animal.query
            .filter(Animal.propriedade_id.in_(propriedades_ids))
            .count()
        )

        atendimentos = (
            Atendimento.query
            .join(Animal)
            .filter(Animal.propriedade_id.in_(propriedades_ids))
            .all()
        )

    total_atendimentos = len(atendimentos)

    contagem_diagnostico = {}
    contagem_mensal = {}

    for atendimento in atendimentos:
        dados = atendimento.dados if isinstance(atendimento.dados, dict) else {}
        diagnostico = (dados.get("diagnostico_principal") or "").strip()

        if diagnostico:
            contagem_diagnostico[diagnostico] = (
                contagem_diagnostico.get(diagnostico, 0) + 1
            )

        if atendimento.data_atendimento:
            chave_mes = atendimento.data_atendimento.strftime("%m/%Y")
            contagem_mensal[chave_mes] = contagem_mensal.get(chave_mes, 0) + 1

    diagnostico_mais_comum = None
    if contagem_diagnostico:
        diagnostico_mais_comum = max(contagem_diagnostico, key=contagem_diagnostico.get)

    def chave_ordenacao_mes(item):
        mes_ano = item[0]
        mes, ano = mes_ano.split("/")
        return (int(ano), int(mes))

    contagem_mensal = dict(
        sorted(contagem_mensal.items(), key=chave_ordenacao_mes)
    )

    return render_template(
        "painel.html",
        propriedades=propriedades,
        total_propriedades=len(propriedades),
        total_animais=total_animais,
        total_atendimentos=total_atendimentos,
        diagnostico_mais_comum=diagnostico_mais_comum,
        contagem_mensal=contagem_mensal,
    )
# ==========================
# 🏡 PROPRIEDADES
# ==========================
@main.route("/propriedades", methods=["GET", "POST"])
def propriedades():
    usuario = obter_usuario_logado()
    if not usuario:
        return redirect(url_for("main.login"))

    if request.method == "POST":
        nome = (request.form.get("nome") or "").strip()
        produtor = (request.form.get("produtor") or "").strip()
        cidade = (request.form.get("cidade") or "").strip()
        estado = (request.form.get("estado") or "").strip().upper()

        if not nome or not produtor:
            flash("Nome e produtor são obrigatórios.", "error")
            return redirect(url_for("main.propriedades"))

        prop = Propriedade(
            nome=nome,
            produtor=produtor,
            cidade=cidade or None,
            estado=estado or None,
        )
        db.session.add(prop)
        db.session.commit()

        # vincula usuário à propriedade
        vinculo = UsuarioPropriedade(
            usuario_id=usuario.id,
            propriedade_id=prop.id,
        )
        db.session.add(vinculo)
        db.session.commit()

        flash("Propriedade criada com sucesso!", "success")
        return redirect(url_for("main.propriedades"))

    # mostra SOMENTE propriedades vinculadas ao usuário

    propriedades = listar_propriedades_do_usuario(usuario)

    return render_template("propriedades.html", propriedades=propriedades)

@main.route("/propriedades/<int:propriedade_id>/excluir")
def excluir_propriedade(propriedade_id):
    usuario = obter_usuario_logado()
    if not usuario:
        return redirect(url_for("main.login"))

    propriedade = Propriedade.query.get_or_404(propriedade_id)

    if not usuario_tem_acesso_propriedade(usuario, propriedade.id):
        flash("Você não tem acesso a essa propriedade.", "error")
        return redirect(url_for("main.propriedades"))

    animais = Animal.query.filter_by(propriedade_id=propriedade.id).count()

    if animais > 0:
        flash(
            "Não é possível excluir a propriedade porque existem animais cadastrados nela.",
            "error",
        )
        return redirect(url_for("main.propriedades"))

    UsuarioPropriedade.query.filter_by(propriedade_id=propriedade.id).delete()

    db.session.delete(propriedade)
    db.session.commit()

    flash("Propriedade excluída com sucesso.", "success")
    return redirect(url_for("main.propriedades"))

# ==========================
# 🐄 LISTAR ANIMAIS (por propriedade)
# ==========================
@main.route("/propriedades/<int:propriedade_id>/animais")
def listar_animais(propriedade_id: int):
   
    usuario = obter_usuario_logado()
    if not usuario:
        return redirect(url_for("main.login"))
    propriedade = Propriedade.query.get_or_404(propriedade_id)

    # acesso: admin ou vinculado à propriedade
    if not usuario_tem_acesso_propriedade(usuario, propriedade.id):
        flash("Você não tem acesso a essa propriedade.", "error")
        return redirect(url_for("main.propriedades"))

    animais = listar_animais_da_propriedade(propriedade.id)

    return render_template("animais.html", propriedade=propriedade, animais=animais)


# ==========================
# 🐄 NOVO ANIMAL
# ==========================

@main.route("/propriedades/<int:propriedade_id>/animais/novo", methods=["GET", "POST"])
def novo_animal(propriedade_id: int):
    usuario = obter_usuario_logado()
    if not usuario:
        return redirect(url_for("main.login"))

    propriedade = Propriedade.query.get_or_404(propriedade_id)

    if not usuario_tem_acesso_propriedade(usuario, propriedade.id):
        flash("Você não tem acesso a essa propriedade.", "error")
        return redirect(url_for("main.propriedades"))

    if request.method == "POST":
        animal, erro = criar_animal(request.form, propriedade.id)

        if erro:
            flash(erro, "error")
            return redirect(request.url)

        flash("Animal cadastrado com sucesso!", "success")
        return redirect(url_for("main.listar_animais", propriedade_id=propriedade.id))

    return render_template("animal_novo.html", propriedade=propriedade)


@main.route("/animais/<int:animal_id>/editar", methods=["GET", "POST"])
def editar_animal(animal_id):
    usuario = obter_usuario_logado()
    if not usuario:
        return redirect(url_for("main.login"))

    animal = Animal.query.get_or_404(animal_id)
    propriedade = Propriedade.query.get_or_404(animal.propriedade_id)

    if not usuario_tem_acesso_propriedade(usuario, propriedade.id):
        flash("Você não tem acesso a essa propriedade.", "error")
        return redirect(url_for("main.propriedades"))

    if request.method == "POST":
        animal.codigo = (request.form.get("codigo") or "").strip()
        animal.nome = (request.form.get("nome") or "").strip() or None
        animal.especie = (request.form.get("especie") or "").strip() or None
        animal.raca = (request.form.get("raca") or "").strip() or None
        animal.sexo = (request.form.get("sexo") or "").strip() or None
        animal.perfil_genetico = (
            request.form.get("perfil_genetico") or ""
        ).strip() or None

        data_nascimento = (request.form.get("data_nascimento") or "").strip()

        if data_nascimento:
            try:
                animal.data_nascimento = datetime.strptime(
                    data_nascimento, "%Y-%m-%d"
                ).date()
            except ValueError:
                flash("Data inválida.", "error")
                return redirect(request.url)
        else:
            animal.data_nascimento = None

        if not animal.codigo:
            flash("O código do animal é obrigatório.", "error")
            return redirect(request.url)

        db.session.commit()

        flash("Animal atualizado com sucesso.", "success")

        return redirect(
            url_for("main.listar_animais", propriedade_id=propriedade.id)
        )

    return render_template(
        "animal_editar.html",
        animal=animal,
        propriedade=propriedade,
    )

@main.route("/animais/<int:animal_id>/excluir")
def excluir_animal(animal_id):
    usuario = obter_usuario_logado()
    if not usuario:
        return redirect(url_for("main.login"))

    animal = Animal.query.get_or_404(animal_id)

    if not usuario_tem_acesso_propriedade(usuario, animal.propriedade_id):
        flash("Você não tem acesso a essa propriedade.", "error")
        return redirect(url_for("main.propriedades"))

    atendimentos = Atendimento.query.filter_by(animal_id=animal.id).count()

    if atendimentos > 0:
        flash(
            "Não é possível excluir o animal porque existem atendimentos vinculados.",
            "error",
        )
        return redirect(
            url_for("main.listar_animais", propriedade_id=animal.propriedade_id)
        )

    propriedade_id = animal.propriedade_id

    db.session.delete(animal)
    db.session.commit()

    flash("Animal excluído com sucesso.", "success")

    return redirect(
        url_for("main.listar_animais", propriedade_id=propriedade_id)
    )

# ==========================
# 📋 PRONTUÁRIO DO ANIMAL
# ==========================
@main.route("/animais/<int:animal_id>")
def prontuario_animal(animal_id: int):
    usuario_id = session.get("usuario_id")
    if not usuario_id:
        return redirect(url_for("main.login"))

    usuario = db.session.get(Usuario, usuario_id)
    if not usuario:
        session.clear()
        return redirect(url_for("main.login"))

    animal = Animal.query.get_or_404(animal_id)

    # acesso: admin ou vinculado à propriedade do animal
    if usuario.perfil != "admin":
        vinculo = UsuarioPropriedade.query.filter_by(
            usuario_id=usuario.id,
            propriedade_id=animal.propriedade_id,
        ).first()
        if not vinculo:
            flash("Você não tem acesso a esse animal.", "error")
            return redirect(url_for("main.propriedades"))

    atendimentos = (
        Atendimento.query
        .filter_by(animal_id=animal.id)
        .order_by(Atendimento.criado_em.desc())
        .all()
    )

    return render_template("animal_prontuario.html", animal=animal, atendimentos=atendimentos)


# ==========================
# 🩺 NOVO ATENDIMENTO (formulário dinâmico)
# ==========================

@main.route("/animais/<int:animal_id>/atendimentos/novo", methods=["GET", "POST"])
def novo_atendimento(animal_id: int):
    usuario = obter_usuario_logado()
    if not usuario:
        return redirect(url_for("main.login"))

    animal = Animal.query.get_or_404(animal_id)

    if not usuario_tem_acesso_animal(usuario, animal):
        flash("Você não tem acesso a esse animal.", "error")
        return redirect(url_for("main.propriedades"))

    perfil = (usuario.perfil or "tecnico").strip()

    # Admin pode simular perfil via URL:
    # /animais/1/atendimentos/novo?perfil=tecnico
    if perfil == "admin":
        perfil = (request.args.get("perfil") or "veterinario").strip()

    formulario = (
        Formulario.query
        .filter(Formulario.ativo.is_(True))
        .filter(Formulario.perfil_alvo.in_([perfil, "ambos"]))
        .order_by(Formulario.id.desc())
        .first()
    )

    if not formulario:
        flash(
            f"Não existe formulário ativo para o perfil '{perfil}'. Crie em /admin/formularios.",
            "error",
        )
        return redirect(url_for("main.painel"))

    campos = (
        CampoFormulario.query
        .filter_by(formulario_id=formulario.id)
        .order_by(CampoFormulario.ordem.asc(), CampoFormulario.id.asc())
        .all()
    )

    if not campos:
        flash(
            f"O formulário ativo para o perfil '{perfil}' não possui campos cadastrados. Verifique em /admin/formularios.",
            "error",
        )
        return redirect(url_for("main.painel"))

    if request.method == "POST":
        dados = {}

        for c in campos:
            if c.tipo == "checkbox":
                valor = True if request.form.get(c.nome_chave) else False
            else:
                valor = (request.form.get(c.nome_chave) or "").strip()

            if c.obrigatorio and (valor == "" or valor is False):
                flash(f"O campo '{c.rotulo}' é obrigatório.", "error")
                return redirect(request.url)

            if c.tipo == "number" and valor != "":
                try:
                    valor = float(valor) if "." in valor else int(valor)
                except ValueError:
                    flash(f"'{c.rotulo}' deve ser numérico.", "error")
                    return redirect(request.url)

            if c.tipo == "date" and valor != "":
                try:
                    datetime.strptime(valor, "%Y-%m-%d")
                except ValueError:
                    flash(f"'{c.rotulo}' deve ser uma data válida.", "error")
                    return redirect(request.url)

            dados[c.nome_chave] = valor

        data_atendimento_str = (request.form.get("data_atendimento") or "").strip()

        if not data_atendimento_str:
            flash("A data do atendimento é obrigatória.", "error")
            return redirect(request.url)

        try:
            data_atendimento = datetime.strptime(
                data_atendimento_str, "%Y-%m-%d"
            ).date()
        except ValueError:
            flash("Data de atendimento inválida.", "error")
            return redirect(request.url)

        atendimento_existente = Atendimento.query.filter_by(
            animal_id=animal.id,
            data_atendimento=data_atendimento,
        ).first()

        duplicado_mesma_data = atendimento_existente is not None

        at = Atendimento(
            animal_id=animal.id,
            tecnico_id=usuario.id,
            formulario_id=formulario.id,
            dados=dados,
            data_atendimento=data_atendimento,
        )
        db.session.add(at)
        db.session.commit()

        arquivos_imagens = request.files.getlist("imagens")

        for arquivo in arquivos_imagens:
            if not arquivo or not arquivo.filename:
                continue

            if not arquivo_imagem_permitido(arquivo.filename):
                flash(
                    f"Arquivo '{arquivo.filename}' não é uma imagem permitida.",
                    "error",
                )
                continue

            caminho_relativo = salvar_imagem_atendimento(arquivo, at.id)
            if not caminho_relativo:
                continue

            imagem = AtendimentoImagem(
                atendimento_id=at.id,
                nome_arquivo=arquivo.filename,
                caminho_arquivo=caminho_relativo,
            )
            db.session.add(imagem)

        db.session.commit()

        if duplicado_mesma_data:
            flash(
                "Atendimento salvo, mas atenção: já existia outro atendimento para este animal nesta mesma data.",
                "error",
            )
        else:
            flash("Atendimento salvo com sucesso!", "success")

        return redirect(url_for("main.prontuario_animal", animal_id=animal.id))

    return render_template(
        "atendimento_novo.html",
        animal=animal,
        formulario=formulario,
        campos=campos,
        atendimento=None,
        modo_edicao=False,
    )
    
# ==========================
# 🧩 ADMIN — FORMULÁRIOS
# ==========================
@main.route("/admin/formularios", methods=["GET", "POST"])
def admin_formularios():
    if not session.get("usuario_id"):
        return redirect(url_for("main.login"))

    usuario = db.session.get(Usuario, session["usuario_id"])
    if not usuario or usuario.perfil != "admin":
        flash("Acesso restrito ao admin.", "error")
        return redirect(url_for("main.painel"))

    if request.method == "POST":
        nome = (request.form.get("nome") or "").strip()
        perfil_alvo = (request.form.get("perfil_alvo") or "tecnico").strip()
        ativo = True if request.form.get("ativo") else False

        if not nome:
            flash("Nome do formulário é obrigatório.", "error")
            return redirect(request.url)

        f = Formulario(
            nome=nome,
            perfil_alvo=perfil_alvo,
            ativo=ativo
        )
        db.session.add(f)
        db.session.commit()

        flash("Formulário criado com sucesso.", "success")
        return redirect(url_for("main.admin_formularios"))

    formularios = Formulario.query.order_by(Formulario.id.desc()).all()

    formularios_info = []
    for f in formularios:
        total_campos = CampoFormulario.query.filter_by(formulario_id=f.id).count()
        total_atendimentos = Atendimento.query.filter_by(formulario_id=f.id).count()

        formularios_info.append({
            "obj": f,
            "total_campos": total_campos,
            "total_atendimentos": total_atendimentos,
        })

    return render_template(
        "admin_formularios.html",
        formularios_info=formularios_info
    )

@main.route("/admin/formularios/<int:formulario_id>/excluir")
def admin_excluir_formulario(formulario_id):
    if not session.get("usuario_id"):
        return redirect(url_for("main.login"))

    usuario = db.session.get(Usuario, session["usuario_id"])
    if not usuario or usuario.perfil != "admin":
        flash("Acesso restrito ao admin.", "error")
        return redirect(url_for("main.painel"))

    formulario = Formulario.query.get_or_404(formulario_id)

    atendimentos = Atendimento.query.filter_by(formulario_id=formulario.id).all()

    pode_excluir = True

    for at in atendimentos:
        usuario_atendimento = Usuario.query.get(at.tecnico_id)

        if usuario_atendimento and usuario_atendimento.perfil != "admin":
            pode_excluir = False
            break

    if not pode_excluir:
        flash(
            "Este formulário já foi utilizado por usuários não-admin e não pode ser excluído. Você pode desativá-lo.",
            "error",
        )
        return redirect(url_for("main.admin_formularios"))

    CampoFormulario.query.filter_by(formulario_id=formulario.id).delete()
    Atendimento.query.filter_by(formulario_id=formulario.id).delete()

    db.session.delete(formulario)
    db.session.commit()

    flash("Formulário excluído com sucesso.", "success")
    return redirect(url_for("main.admin_formularios"))

@main.route("/admin/formularios/<int:formulario_id>/toggle_ativo")
def admin_toggle_formulario_ativo(formulario_id):
    if not session.get("usuario_id"):
        return redirect(url_for("main.login"))

    usuario = db.session.get(Usuario, session["usuario_id"])
    if not usuario or usuario.perfil != "admin":
        flash("Acesso restrito ao admin.", "error")
        return redirect(url_for("main.painel"))

    formulario = Formulario.query.get_or_404(formulario_id)

    total_campos = CampoFormulario.query.filter_by(formulario_id=formulario.id).count()

    # Se estiver tentando ativar um formulário sem campos, bloqueia
    if not formulario.ativo and total_campos == 0:
        flash(
            "Não é possível ativar um formulário sem campos cadastrados.",
            "error",
        )
        return redirect(url_for("main.admin_formularios"))

    formulario.ativo = not formulario.ativo
    db.session.commit()

    if formulario.ativo:
        flash("Formulário ativado com sucesso.", "success")
    else:
        flash("Formulário desativado com sucesso.", "success")

    return redirect(url_for("main.admin_formularios"))

# ==========================
# 👤 ADMIN — USUÁRIOS
# ==========================
@main.route("/admin/usuarios", methods=["GET", "POST"])
def admin_usuarios():
    usuario = obter_usuario_logado()
    if not usuario or usuario.perfil != "admin":
        flash("Acesso restrito ao admin.", "error")
        return redirect(url_for("main.painel"))

    if request.method == "POST":
        nome = (request.form.get("nome") or "").strip()
        email = (request.form.get("email") or "").strip().lower()
        senha = (request.form.get("senha") or "").strip()
        perfil = (request.form.get("perfil") or "tecnico").strip()

        if not nome or not email or not senha:
            flash("Nome, email e senha são obrigatórios.", "error")
            return redirect(request.url)

        usuario_existente = Usuario.query.filter_by(email=email).first()
        if usuario_existente:
            flash("Já existe um usuário com esse email.", "error")
            return redirect(request.url)

        novo_usuario = Usuario(
            nome=nome,
            email=email,
            perfil=perfil
        )
        novo_usuario.set_password(senha)

        db.session.add(novo_usuario)
        db.session.commit()

        flash("Usuário criado com sucesso.", "success")
        return redirect(url_for("main.admin_usuarios"))

    usuarios = Usuario.query.order_by(Usuario.id.desc()).all()
    return render_template("admin_usuarios.html", usuarios=usuarios)

@main.route("/admin/usuarios/<int:usuario_id>/propriedades", methods=["GET", "POST"])
def admin_usuario_propriedades(usuario_id):

    usuario_logado = obter_usuario_logado()
    if not usuario_logado or usuario_logado.perfil != "admin":
        flash("Acesso restrito ao admin.", "error")
        return redirect(url_for("main.painel"))

    usuario = Usuario.query.get_or_404(usuario_id)

    propriedades = Propriedade.query.order_by(Propriedade.nome.asc()).all()

    if request.method == "POST":

        selecionadas = request.form.getlist("propriedades")

        UsuarioPropriedade.query.filter_by(usuario_id=usuario.id).delete()

        for prop_id in selecionadas:
            vinculo = UsuarioPropriedade(
                usuario_id=usuario.id,
                propriedade_id=int(prop_id)
            )
            db.session.add(vinculo)

        db.session.commit()

        flash("Vínculos atualizados com sucesso.", "success")
        return redirect(url_for("main.admin_usuarios"))

    vinculadas = {
        v.propriedade_id
        for v in UsuarioPropriedade.query.filter_by(usuario_id=usuario.id).all()
    }

    return render_template(
        "admin_usuario_propriedades.html",
        usuario=usuario,
        propriedades=propriedades,
        vinculadas=vinculadas
    )

@main.route("/admin/usuarios/<int:usuario_id>/editar", methods=["GET", "POST"])
def admin_editar_usuario(usuario_id):
    usuario_logado = obter_usuario_logado()
    if not usuario_logado or usuario_logado.perfil != "admin":
        flash("Acesso restrito ao admin.", "error")
        return redirect(url_for("main.painel"))

    usuario = Usuario.query.get_or_404(usuario_id)

    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        perfil = (request.form.get("perfil") or "tecnico").strip()
        senha = (request.form.get("senha") or "").strip()

        if not email:
            flash("Email é obrigatório.", "error")
            return redirect(request.url)

        usuario_existente = Usuario.query.filter(
            Usuario.email == email,
            Usuario.id != usuario.id
        ).first()

        if usuario_existente:
            flash("Já existe outro usuário com esse email.", "error")
            return redirect(request.url)

        usuario.email = email
        usuario.perfil = perfil

        if senha:
            usuario.set_password(senha)

        db.session.commit()

        flash("Usuário atualizado com sucesso.", "success")
        return redirect(url_for("main.admin_usuarios"))

    return render_template("admin_usuario_editar.html", usuario=usuario)


@main.route("/admin/usuarios/<int:usuario_id>/excluir")
def admin_excluir_usuario(usuario_id):
    usuario_logado = obter_usuario_logado()
    if not usuario_logado or usuario_logado.perfil != "admin":
        flash("Acesso restrito ao admin.", "error")
        return redirect(url_for("main.painel"))

    usuario = Usuario.query.get_or_404(usuario_id)

    if usuario.id == usuario_logado.id:
        flash("Você não pode excluir seu próprio usuário.", "error")
        return redirect(url_for("main.admin_usuarios"))

    atendimentos = Atendimento.query.filter_by(tecnico_id=usuario.id).count()
    if atendimentos > 0:
        flash("Não é possível excluir este usuário porque existem atendimentos vinculados.", "error")
        return redirect(url_for("main.admin_usuarios"))

    UsuarioPropriedade.query.filter_by(usuario_id=usuario.id).delete()

    db.session.delete(usuario)
    db.session.commit()

    flash("Usuário excluído com sucesso.", "success")
    return redirect(url_for("main.admin_usuarios"))

@main.route("/admin/campos/<int:campo_id>/editar", methods=["GET", "POST"])
def admin_editar_campo(campo_id):
    if not session.get("usuario_id"):
        return redirect(url_for("main.login"))

    usuario = db.session.get(Usuario, session["usuario_id"])
    if not usuario or usuario.perfil != "admin":
        flash("Acesso restrito ao admin.", "error")
        return redirect(url_for("main.painel"))

    campo = CampoFormulario.query.get_or_404(campo_id)
    formulario = Formulario.query.get_or_404(campo.formulario_id)

    if request.method == "POST":
        campo.rotulo = (request.form.get("rotulo") or "").strip()
        campo.nome_chave = (request.form.get("nome_chave") or "").strip()
        campo.tipo = (request.form.get("tipo") or "text").strip()
        campo.obrigatorio = True if request.form.get("obrigatorio") else False

        ordem = (request.form.get("ordem") or "0").strip()

        try:
            campo.ordem = int(ordem)
        except ValueError:
            campo.ordem = 0

        opcoes_raw = (request.form.get("opcoes") or "").strip()

        if campo.tipo == "select":
            if opcoes_raw.startswith("["):
                try:
                    campo.opcoes = json.loads(opcoes_raw)
                except Exception:
                    flash("Opções inválidas.", "error")
                    return redirect(request.url)
            elif opcoes_raw:
                campo.opcoes = [x.strip() for x in opcoes_raw.split(",") if x.strip()]
        else:
            campo.opcoes = None

        db.session.commit()

        flash("Campo atualizado com sucesso.", "success")
        return redirect(url_for("main.admin_formulario_campos", formulario_id=formulario.id))

    return render_template(
        "admin_campo_editar.html",
        campo=campo,
        formulario=formulario
    )

@main.route("/admin/campos/<int:campo_id>/excluir")
def admin_excluir_campo(campo_id):
    if not session.get("usuario_id"):
        return redirect(url_for("main.login"))

    usuario = db.session.get(Usuario, session["usuario_id"])
    if not usuario or usuario.perfil != "admin":
        flash("Acesso restrito ao admin.", "error")
        return redirect(url_for("main.painel"))

    campo = CampoFormulario.query.get_or_404(campo_id)
    formulario_id = campo.formulario_id

    db.session.delete(campo)
    db.session.commit()

    flash("Campo excluído.", "success")
    return redirect(url_for("main.admin_formulario_campos", formulario_id=formulario_id))

@main.route("/admin/formularios/<int:formulario_id>/campos", methods=["GET", "POST"])
def admin_formulario_campos(formulario_id: int):
    if not session.get("usuario_id"):
        return redirect(url_for("main.login"))

    usuario = db.session.get(Usuario, session["usuario_id"])
    if not usuario or usuario.perfil != "admin":
        flash("Acesso restrito ao admin.", "error")
        return redirect(url_for("main.painel"))

    formulario = Formulario.query.get_or_404(formulario_id)

    if request.method == "POST":
        rotulo = (request.form.get("rotulo") or "").strip()
        nome_chave = (request.form.get("nome_chave") or "").strip()
        tipo = (request.form.get("tipo") or "text").strip()
        obrigatorio = True if request.form.get("obrigatorio") else False
        ordem = (request.form.get("ordem") or "0").strip()
        opcoes_raw = (request.form.get("opcoes") or "").strip()

        if not rotulo or not nome_chave:
            flash("Rótulo e nome_chave são obrigatórios.", "error")
            return redirect(request.url)

        try:
            ordem_int = int(ordem) if ordem else 0
        except ValueError:
            ordem_int = 0

        opcoes = None
        if tipo == "select":
            if opcoes_raw.startswith("["):
                try:
                    opcoes = json.loads(opcoes_raw)
                except Exception:
                    flash("Opções inválidas. Use JSON válido ou texto separado por vírgula.", "error")
                    return redirect(request.url)
            elif opcoes_raw:
                opcoes = [x.strip() for x in opcoes_raw.split(",") if x.strip()]

        campo = CampoFormulario(
            formulario_id=formulario.id,
            rotulo=rotulo,
            nome_chave=nome_chave,
            tipo=tipo,
            obrigatorio=obrigatorio,
            opcoes=opcoes,
            ordem=ordem_int,
        )
        db.session.add(campo)
        db.session.commit()

        flash("Campo criado com sucesso.", "success")
        return redirect(url_for("main.admin_formulario_campos", formulario_id=formulario.id))

    campos = (
        CampoFormulario.query
        .filter_by(formulario_id=formulario.id)
        .order_by(CampoFormulario.ordem.asc(), CampoFormulario.id.asc())
        .all()
    )
    return render_template("admin_formulario_campos.html", formulario=formulario, campos=campos)

from sqlalchemy import func, and_

@main.route("/atendimentos/novo", methods=["GET"])
def selecionar_atendimento():
    usuario = obter_usuario_logado()
    if not usuario:
        return redirect(url_for("main.login"))

    propriedades = listar_propriedades_do_usuario(usuario)
    propriedade_id = request.args.get("propriedade_id", type=int)
    animais_info = []

    if propriedade_id:
        if not usuario_tem_acesso_propriedade(usuario, propriedade_id):
            flash("Você não tem acesso a essa propriedade.", "error")
            return redirect(url_for("main.propriedades"))

        animais = listar_animais_da_propriedade(propriedade_id)
        animal_ids = [a.id for a in animais]

        ultimos_atendimentos_por_animal = {}

        if animal_ids:
            subquery = (
                db.session.query(
                    Atendimento.animal_id.label("animal_id"),
                    func.max(Atendimento.data_atendimento).label("max_data")
                )
                .filter(Atendimento.animal_id.in_(animal_ids))
                .group_by(Atendimento.animal_id)
                .subquery()
            )

            ultimos_atendimentos = (
                db.session.query(Atendimento)
                .join(
                    subquery,
                    and_(
                        Atendimento.animal_id == subquery.c.animal_id,
                        Atendimento.data_atendimento == subquery.c.max_data
                    )
                )
                .all()
            )

            ultimos_atendimentos_por_animal = {
                at.animal_id: at for at in ultimos_atendimentos
            }

        animais_info = [
            {
                "animal": animal,
                "ultimo_atendimento": ultimos_atendimentos_por_animal.get(animal.id)
            }
            for animal in animais
        ]

    return render_template(
        "atendimento_selecionar.html",
        propriedades=propriedades,
        animais_info=animais_info,
        propriedade_id=propriedade_id,
    )

@main.route("/atendimento/<int:id>/excluir")
def excluir_atendimento(id):

    usuario = obter_usuario_logado()
    if not usuario:
        return redirect(url_for("main.login"))

    if usuario.perfil not in ["admin", "veterinario"]:
        flash("Você não tem permissão para excluir atendimentos.", "error")
        return redirect(url_for("main.painel"))

    atendimento = Atendimento.query.get_or_404(id)
    animal_id = atendimento.animal_id

    db.session.delete(atendimento)
    db.session.commit()

    flash("Atendimento excluído com sucesso.", "success")
    return redirect(url_for("main.prontuario_animal", animal_id=animal_id))

@main.route("/atendimento/<int:id>/editar", methods=["GET", "POST"])
def editar_atendimento(id):
    usuario = obter_usuario_logado()
    if not usuario:
        return redirect(url_for("main.login"))

    atendimento = Atendimento.query.get_or_404(id)
    animal = Animal.query.get_or_404(atendimento.animal_id)

    if not usuario_tem_acesso_animal(usuario, animal):
        flash("Você não tem acesso a esse animal.", "error")
        return redirect(url_for("main.propriedades"))

    if atendimento.bloqueado_em:
        flash("Este atendimento está bloqueado e não pode ser editado.", "error")
        return redirect(url_for("main.prontuario_animal", animal_id=animal.id))

    formulario = Formulario.query.get_or_404(atendimento.formulario_id)

    campos = (
        CampoFormulario.query
        .filter_by(formulario_id=formulario.id)
        .order_by(CampoFormulario.ordem.asc(), CampoFormulario.id.asc())
        .all()
    )

    if request.method == "POST":
        dados = {}

        for c in campos:
            if c.tipo == "checkbox":
                valor = True if request.form.get(c.nome_chave) else False
            else:
                valor = (request.form.get(c.nome_chave) or "").strip()

            if c.obrigatorio and (valor == "" or valor is False):
                flash(f"O campo '{c.rotulo}' é obrigatório.", "error")
                return redirect(request.url)

            if c.tipo == "number" and valor != "":
                try:
                    valor = float(valor) if "." in valor else int(valor)
                except ValueError:
                    flash(f"'{c.rotulo}' deve ser numérico.", "error")
                    return redirect(request.url)

            if c.tipo == "date" and valor != "":
                try:
                    datetime.strptime(valor, "%Y-%m-%d")
                except ValueError:
                    flash(f"'{c.rotulo}' deve ser uma data válida.", "error")
                    return redirect(request.url)

            dados[c.nome_chave] = valor

        data_atendimento_str = (request.form.get("data_atendimento") or "").strip()

        if not data_atendimento_str:
            flash("A data do atendimento é obrigatória.", "error")
            return redirect(request.url)

        try:
            data_atendimento = datetime.strptime(data_atendimento_str, "%Y-%m-%d").date()
        except ValueError:
            flash("Data de atendimento inválida.", "error")
            return redirect(request.url)

        atendimento.data_atendimento = data_atendimento
        atendimento.dados = dados

        db.session.commit()

        arquivos_imagens = request.files.getlist("imagens")

        for arquivo in arquivos_imagens:
            if not arquivo or not arquivo.filename:
                continue

            if not arquivo_imagem_permitido(arquivo.filename):
                flash(
                    f"Arquivo '{arquivo.filename}' não é uma imagem permitida.",
                    "error",
                )
                continue

            caminho_relativo = salvar_imagem_atendimento(arquivo, atendimento.id)
            if not caminho_relativo:
                continue

            imagem = AtendimentoImagem(
                atendimento_id=atendimento.id,
                nome_arquivo=arquivo.filename,
                caminho_arquivo=caminho_relativo,
            )
            db.session.add(imagem)

        db.session.commit()

        flash("Atendimento atualizado com sucesso!", "success")
        return redirect(url_for("main.prontuario_animal", animal_id=animal.id))

    return render_template(
        "atendimento_novo.html",
        animal=animal,
        formulario=formulario,
        campos=campos,
        atendimento=atendimento,
        modo_edicao=True,
    )
@main.route("/relatorios/epidemiologico")
def relatorio_epidemiologico():

    usuario = obter_usuario_logado()
    if not usuario:
        return redirect(url_for("main.login"))

    propriedade_id = request.args.get("propriedade_id", type=int)
    data_inicio = request.args.get("data_inicio")
    data_fim = request.args.get("data_fim")

    data_inicio_convertida = None
    data_fim_convertida = None

    if usuario.perfil == "admin":
        propriedades = Propriedade.query.order_by(Propriedade.nome.asc()).all()
    else:
        propriedades = listar_propriedades_do_usuario(usuario)

    propriedades_ids = [p.id for p in propriedades]

    if usuario.perfil != "admin" and propriedade_id and propriedade_id not in propriedades_ids:
        flash("Você não tem acesso a essa propriedade.", "error")
        return redirect(url_for("main.relatorio_epidemiologico"))

    query = (
        Atendimento.query
        .join(Animal, Atendimento.animal_id == Animal.id)
        .join(Propriedade, Animal.propriedade_id == Propriedade.id)
    )

    if usuario.perfil == "admin":
        if propriedade_id:
            query = query.filter(Animal.propriedade_id == propriedade_id)
    else:
        query = query.filter(Animal.propriedade_id.in_(propriedades_ids))
        if propriedade_id:
            query = query.filter(Animal.propriedade_id == propriedade_id)

    if data_inicio:
        try:
            data_inicio_convertida = datetime.strptime(data_inicio, "%Y-%m-%d").date()
            query = query.filter(Atendimento.data_atendimento >= data_inicio_convertida)
        except ValueError:
            flash("Data inicial inválida.", "error")
            return redirect(url_for("main.relatorio_epidemiologico"))

    if data_fim:
        try:
            data_fim_convertida = datetime.strptime(data_fim, "%Y-%m-%d").date()
            query = query.filter(Atendimento.data_atendimento <= data_fim_convertida)
        except ValueError:
            flash("Data final inválida.", "error")
            return redirect(url_for("main.relatorio_epidemiologico"))

    atendimentos = query.all()

    contagem_diagnostico = {}
    contagem_categoria = {}
    contagem_desfecho = {}
    contagem_mensal = {}
    contagem_propriedade = {}
    contagem_genetica = {}

    for atendimento in atendimentos:

        dados = atendimento.dados if isinstance(atendimento.dados, dict) else {}

        diagnostico = (dados.get("diagnostico_principal") or "").strip()
        categoria = (dados.get("categoria_diagnostico") or "").strip()
        desfecho = (dados.get("desfecho") or "").strip()

        if diagnostico:
            contagem_diagnostico[diagnostico] = contagem_diagnostico.get(diagnostico, 0) + 1

        if categoria:
            contagem_categoria[categoria] = contagem_categoria.get(categoria, 0) + 1

        if desfecho:
            contagem_desfecho[desfecho] = contagem_desfecho.get(desfecho, 0) + 1

        if atendimento.data_atendimento:
            chave_mes = atendimento.data_atendimento.strftime("%m/%Y")
            contagem_mensal[chave_mes] = contagem_mensal.get(chave_mes, 0) + 1

        if atendimento.animal and atendimento.animal.propriedade:
            nome_propriedade = atendimento.animal.propriedade.nome
            contagem_propriedade[nome_propriedade] = contagem_propriedade.get(nome_propriedade, 0) + 1

        if diagnostico and atendimento.animal:
            perfil = (atendimento.animal.perfil_genetico or "Não informado").strip()
            chave = f"{perfil} | {diagnostico}"
            contagem_genetica[chave] = contagem_genetica.get(chave, 0) + 1

    contagem_diagnostico = dict(sorted(contagem_diagnostico.items(), key=lambda x: x[1], reverse=True))
    contagem_categoria = dict(sorted(contagem_categoria.items(), key=lambda x: x[1], reverse=True))
    contagem_desfecho = dict(sorted(contagem_desfecho.items(), key=lambda x: x[1], reverse=True))
    contagem_propriedade = dict(sorted(contagem_propriedade.items(), key=lambda x: x[1], reverse=True))
    contagem_genetica = dict(sorted(contagem_genetica.items(), key=lambda x: x[1], reverse=True))

    def chave_ordenacao_mes(item):
        mes, ano = item[0].split("/")
        return (int(ano), int(mes))

    contagem_mensal = dict(sorted(contagem_mensal.items(), key=chave_ordenacao_mes))

    propriedade_selecionada = None
    if propriedade_id:
        propriedade_selecionada = next((p for p in propriedades if p.id == propriedade_id), None)

    # ==========================
    # RISCO EPIDEMIOLÓGICO
    # ==========================

    if propriedade_id:
        propriedades_para_risco = [p for p in propriedades if p.id == propriedade_id]
    else:
        propriedades_para_risco = propriedades

    risco_propriedades = []

    for prop in propriedades_para_risco:

        total_animais_prop = Animal.query.filter_by(propriedade_id=prop.id).count()

        total_atendimentos_prop = (
            Atendimento.query
            .join(Animal, Atendimento.animal_id == Animal.id)
            .filter(Animal.propriedade_id == prop.id)
        )

        if data_inicio_convertida:
            total_atendimentos_prop = total_atendimentos_prop.filter(
                Atendimento.data_atendimento >= data_inicio_convertida
            )

        if data_fim_convertida:
            total_atendimentos_prop = total_atendimentos_prop.filter(
                Atendimento.data_atendimento <= data_fim_convertida
            )

        total_atendimentos_prop = total_atendimentos_prop.count()

        taxa = 0
        if total_animais_prop > 0:
            taxa = round((total_atendimentos_prop / total_animais_prop) * 100, 2)

        if taxa <= 20:
            classificacao = "Baixo"
        elif taxa <= 50:
            classificacao = "Moderado"
        else:
            classificacao = "Alto"

        risco_propriedades.append({
            "nome": prop.nome,
            "total_animais": total_animais_prop,
            "total_atendimentos": total_atendimentos_prop,
            "taxa": taxa,
            "classificacao": classificacao
        })

    risco_propriedades = sorted(
        risco_propriedades,
        key=lambda x: x["taxa"],
        reverse=True
    )

    # ==========================
    # RESUMO EXECUTIVO
    # ==========================

    diagnostico_top = None
    propriedade_top = None
    genetica_top = None

    if contagem_diagnostico:
        diagnostico_top = max(contagem_diagnostico, key=contagem_diagnostico.get)

    if contagem_propriedade:
        propriedade_top = max(contagem_propriedade, key=contagem_propriedade.get)

    if contagem_genetica:
        genetica_top = max(contagem_genetica, key=contagem_genetica.get)

    return render_template(
        "relatorio_epidemiologico.html",
        contagem_diagnostico=contagem_diagnostico,
        contagem_categoria=contagem_categoria,
        contagem_desfecho=contagem_desfecho,
        contagem_mensal=contagem_mensal,
        contagem_propriedade=contagem_propriedade,
        contagem_genetica=contagem_genetica,
        risco_propriedades=risco_propriedades,
        diagnostico_top=diagnostico_top,
        propriedade_top=propriedade_top,
        genetica_top=genetica_top,
        total_atendimentos=len(atendimentos),
        propriedades=propriedades,
        propriedade_id=propriedade_id,
        propriedade_selecionada=propriedade_selecionada,
    )

@main.route("/relatorios/epidemiologico/pdf", methods=["POST"])
def relatorio_epidemiologico_pdf():

    usuario = obter_usuario_logado()
    if not usuario:
        return redirect(url_for("main.login"))

    propriedade_id = request.form.get("propriedade_id", type=int)
    data_inicio = request.form.get("data_inicio")
    data_fim = request.form.get("data_fim")

    grafico_diagnostico_img = request.form.get("grafico_diagnostico_img")
    grafico_mensal_img = request.form.get("grafico_mensal_img")

    if usuario.perfil == "admin":
        propriedades = Propriedade.query.order_by(Propriedade.nome.asc()).all()
    else:
        propriedades = listar_propriedades_do_usuario(usuario)

    propriedades_ids = [p.id for p in propriedades]

    query = (
        Atendimento.query
        .join(Animal, Atendimento.animal_id == Animal.id)
        .join(Propriedade, Animal.propriedade_id == Propriedade.id)
    )

    if usuario.perfil == "admin":
        if propriedade_id:
            query = query.filter(Animal.propriedade_id == propriedade_id)
    else:
        query = query.filter(Animal.propriedade_id.in_(propriedades_ids))
        if propriedade_id:
            query = query.filter(Animal.propriedade_id == propriedade_id)

    if data_inicio:
        data_inicio = datetime.strptime(data_inicio, "%Y-%m-%d").date()
        query = query.filter(Atendimento.data_atendimento >= data_inicio)

    if data_fim:
        data_fim = datetime.strptime(data_fim, "%Y-%m-%d").date()
        query = query.filter(Atendimento.data_atendimento <= data_fim)

    atendimentos = query.all()

    contagem_diagnostico = {}
    contagem_categoria = {}
    contagem_desfecho = {}
    contagem_mensal = {}
    contagem_propriedade = {}
    contagem_genetica = {}

    for atendimento in atendimentos:

        dados = atendimento.dados if isinstance(atendimento.dados, dict) else {}

        diagnostico = (dados.get("diagnostico_principal") or "").strip()
        categoria = (dados.get("categoria_diagnostico") or "").strip()
        desfecho = (dados.get("desfecho") or "").strip()

        if diagnostico:
            contagem_diagnostico[diagnostico] = contagem_diagnostico.get(diagnostico, 0) + 1

        if categoria:
            contagem_categoria[categoria] = contagem_categoria.get(categoria, 0) + 1

        if desfecho:
            contagem_desfecho[desfecho] = contagem_desfecho.get(desfecho, 0) + 1

        if atendimento.data_atendimento:
            chave_mes = atendimento.data_atendimento.strftime("%m/%Y")
            contagem_mensal[chave_mes] = contagem_mensal.get(chave_mes, 0) + 1

        if atendimento.animal and atendimento.animal.propriedade:
            nome_prop = atendimento.animal.propriedade.nome
            contagem_propriedade[nome_prop] = contagem_propriedade.get(nome_prop, 0) + 1

        if diagnostico and atendimento.animal:
            perfil = (atendimento.animal.perfil_genetico or "Não informado").strip()
            chave = f"{perfil} | {diagnostico}"
            contagem_genetica[chave] = contagem_genetica.get(chave, 0) + 1

    contagem_diagnostico = dict(sorted(contagem_diagnostico.items(), key=lambda x: x[1], reverse=True))
    contagem_categoria = dict(sorted(contagem_categoria.items(), key=lambda x: x[1], reverse=True))
    contagem_desfecho = dict(sorted(contagem_desfecho.items(), key=lambda x: x[1], reverse=True))
    contagem_propriedade = dict(sorted(contagem_propriedade.items(), key=lambda x: x[1], reverse=True))
    contagem_genetica = dict(sorted(contagem_genetica.items(), key=lambda x: x[1], reverse=True))

    def ordenar_mes(item):
        mes, ano = item[0].split("/")
        return (int(ano), int(mes))

    contagem_mensal = dict(sorted(contagem_mensal.items(), key=ordenar_mes))

    # ================================
    # RESUMO EXECUTIVO
    # ================================

    diagnostico_top = max(contagem_diagnostico, key=contagem_diagnostico.get) if contagem_diagnostico else None
    propriedade_top = max(contagem_propriedade, key=contagem_propriedade.get) if contagem_propriedade else None
    genetica_top = max(contagem_genetica, key=contagem_genetica.get) if contagem_genetica else None

    propriedade_selecionada = None
    if propriedade_id:
        propriedade_selecionada = next((p for p in propriedades if p.id == propriedade_id), None)

    config_sistema = ConfiguracaoSistema.query.first()

    html = render_template(
        "relatorio_epidemiologico_pdf.html",

        contagem_diagnostico=contagem_diagnostico,
        contagem_categoria=contagem_categoria,
        contagem_desfecho=contagem_desfecho,
        contagem_mensal=contagem_mensal,
        contagem_propriedade=contagem_propriedade,
        contagem_genetica=contagem_genetica,

        diagnostico_top=diagnostico_top,
        propriedade_top=propriedade_top,
        genetica_top=genetica_top,

        grafico_diagnostico_img=grafico_diagnostico_img,
        grafico_mensal_img=grafico_mensal_img,

        total_atendimentos=len(atendimentos),
        propriedade_selecionada=propriedade_selecionada,
        data_inicio=data_inicio,
        data_fim=data_fim,

        config_sistema=config_sistema,
        gerado_em=datetime.now()
    )

    pdf = HTML(string=html).write_pdf()

    return Response(
        pdf,
        mimetype="application/pdf",
        headers={"Content-Disposition": "inline; filename=relatorio_epidemiologico.pdf"}
    )

@main.route("/admin/configuracoes", methods=["GET", "POST"])
def admin_configuracoes():
    usuario = obter_usuario_logado()
    if not usuario or usuario.perfil != "admin":
        flash("Acesso restrito.", "error")
        return redirect(url_for("main.painel"))

    config = ConfiguracaoSistema.query.first()

    if not config:
        config = ConfiguracaoSistema()
        db.session.add(config)
        db.session.commit()

    if request.method == "POST":
        import os
        from werkzeug.utils import secure_filename

        config.nome_plataforma = (request.form.get("nome_plataforma") or "").strip() or None
        config.subtitulo = (request.form.get("subtitulo") or "").strip() or None
        config.texto_banner = (request.form.get("texto_banner") or "").strip() or None
        config.aviso_sanitario = (request.form.get("aviso_sanitario") or "").strip() or None
        config.rodape = (request.form.get("rodape") or "").strip() or None

        arquivo_logo = request.files.get("logo")

        if arquivo_logo and arquivo_logo.filename:
            extensoes_permitidas = {"png", "jpg", "jpeg", "webp"}
            nome_original = secure_filename(arquivo_logo.filename)
            extensao = nome_original.rsplit(".", 1)[-1].lower() if "." in nome_original else ""

            if extensao not in extensoes_permitidas:
                flash("Formato de logo inválido. Envie PNG, JPG, JPEG ou WEBP.", "error")
                return redirect(url_for("main.admin_configuracoes"))

            pasta_logo = os.path.join("app", "static", "uploads", "logo")
            os.makedirs(pasta_logo, exist_ok=True)

            nome_arquivo = f"logo_sistema.{extensao}"
            caminho_absoluto = os.path.join(pasta_logo, nome_arquivo)
            arquivo_logo.save(caminho_absoluto)

            config.logo = f"uploads/logo/{nome_arquivo}"

        db.session.commit()

        flash("Configurações atualizadas.", "success")
        return redirect(url_for("main.admin_configuracoes"))

    return render_template(
        "admin_configuracoes.html",
        config=config
    )

ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

def arquivo_imagem_permitido(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS

def salvar_imagem_atendimento(arquivo, atendimento_id: int) -> str | None:
    if not arquivo or not arquivo.filename:
        return None

    if not arquivo_imagem_permitido(arquivo.filename):
        return None

    extensao = arquivo.filename.rsplit(".", 1)[1].lower()
    nome_seguro = secure_filename(arquivo.filename)
    nome_final = f"{atendimento_id}_{uuid.uuid4().hex}.{extensao}"

    pasta_destino = os.path.join(
        current_app.config["UPLOAD_FOLDER"],
        "atendimentos",
        str(atendimento_id),
    )
    os.makedirs(pasta_destino, exist_ok=True)

    caminho_absoluto = os.path.join(pasta_destino, nome_final)
    arquivo.save(caminho_absoluto)

    caminho_relativo = os.path.join(
        "uploads",
        "atendimentos",
        str(atendimento_id),
        nome_final,
    ).replace("\\", "/")

    return caminho_relativo