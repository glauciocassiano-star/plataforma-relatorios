from datetime import datetime

from flask import flash, redirect, render_template, request, url_for
from sqlalchemy import func

from .base import main
from .. import db
from ..helpers.auth import obter_usuario_logado
from ..helpers.decorators import (
    acesso_animal,
    acesso_atendimento,
    login_obrigatorio,
)
from ..models import Animal, Atendimento, Exame, Formulario, Propriedade
from ..services.animal_service import listar_animais_da_propriedade
from ..services.propriedade_service import listar_propriedades_do_usuario
from ..utils.pdf import gerar_pdf_atendimento
from ..utils.uploads import salvar_arquivo_exame, salvar_imagem_atendimento


@main.route("/atendimentos")
@login_obrigatorio
def selecionar_atendimento():
    usuario = obter_usuario_logado()
    propriedades = listar_propriedades_do_usuario(usuario)

    propriedade_id = request.args.get("propriedade_id", type=int)
    animais_info = []

    if propriedade_id:
        propriedade = Propriedade.query.get_or_404(propriedade_id)
        animais = listar_animais_da_propriedade(propriedade_id)

        for animal in animais:
            ultimo_atendimento = (
                Atendimento.query
                .filter(
                    Atendimento.animal_id == animal.id,
                    Atendimento.data_atendimento.isnot(None)
                )
                .order_by(
                    Atendimento.data_atendimento.desc(),
                    Atendimento.criado_em.desc()
                )
                .first()
            )

            animais_info.append({
                "animal": animal,
                "ultimo_atendimento": ultimo_atendimento
            })

    return render_template(
        "selecionar_atendimento.html",
        propriedades=propriedades,
        propriedade_id=propriedade_id,
        animais_info=animais_info,
    )

@main.route("/animais/<int:animal_id>/atendimentos/novo", methods=["GET", "POST"])
@login_obrigatorio
@acesso_animal
def novo_atendimento(animal_id):
    usuario = obter_usuario_logado()
    animal = Animal.query.get_or_404(animal_id)

    perfil = (usuario.perfil or "tecnico").strip().lower()

    if perfil == "admin_master":
        perfil_simulado = (request.args.get("perfil") or "veterinario").strip().lower()
        if perfil_simulado not in ["tecnico", "veterinario"]:
            perfil_simulado = "veterinario"
        perfil = perfil_simulado

    formularios_disponiveis = (
        Formulario.query
        .filter(
            Formulario.ativo.is_(True),
            Formulario.perfil_alvo.in_([perfil, "ambos"])
        )
        .order_by(Formulario.nome.asc())
        .all()
    )

    formulario_id = request.values.get("formulario_id", type=int)

    formulario = None
    if formulario_id:
        formulario = next(
            (f for f in formularios_disponiveis if f.id == formulario_id),
            None
        )

    if not formulario and formularios_disponiveis:
        formulario = formularios_disponiveis[0]

    campos = sorted(formulario.campos, key=lambda c: (c.ordem or 0, c.id)) if formulario else []

    if request.method == "POST":
        if not formulario:
            flash("Selecione um formulário válido para continuar.", "error")
            return redirect(request.url)

        dados = {}
        erro = None

        data_atendimento_str = (request.form.get("data_atendimento") or "").strip()
        if not data_atendimento_str:
            flash("A data do atendimento é obrigatória.", "error")
            return redirect(request.url)

        try:
            data_atendimento = datetime.strptime(data_atendimento_str, "%Y-%m-%d").date()
        except ValueError:
            flash("Data do atendimento inválida.", "error")
            return redirect(request.url)

        atendimento_existente = Atendimento.query.filter_by(
            animal_id=animal.id,
            data_atendimento=data_atendimento,
        ).first()

        duplicado_mesma_data = atendimento_existente is not None

        for campo in campos:
            valor = request.form.get(campo.nome_chave)

            if campo.tipo == "checkbox":
                valor = campo.nome_chave in request.form

            elif campo.tipo == "number":
                if valor not in (None, ""):
                    try:
                        valor = float(valor) if "." in valor else int(valor)
                    except ValueError:
                        erro = f"O campo '{campo.rotulo}' deve ser numérico."
                        break
                else:
                    valor = None

            elif campo.tipo == "date":
                if valor:
                    try:
                        datetime.strptime(valor, "%Y-%m-%d")
                    except ValueError:
                        erro = f"O campo '{campo.rotulo}' possui uma data inválida."
                        break
                else:
                    valor = None

            else:
                valor = (valor or "").strip() or None

            if campo.obrigatorio:
                vazio = (
                    valor is None
                    or valor == ""
                    or (campo.tipo == "checkbox" and valor is False)
                )
                if vazio:
                    erro = f"O campo '{campo.rotulo}' é obrigatório."
                    break

            dados[campo.nome_chave] = valor

        if erro:
            flash(erro, "error")
            return redirect(request.url)

        atendimento = Atendimento(
            animal_id=animal.id,
            tecnico_id=usuario.id,
            formulario_id=formulario.id,
            dados=dados,
            data_atendimento=data_atendimento,
        )

        db.session.add(atendimento)
        db.session.commit()

        imagens = request.files.getlist("imagens")
        for imagem in imagens:
            if imagem and imagem.filename:
                salvar_imagem_atendimento(atendimento.id, imagem)

        if duplicado_mesma_data:
            flash(
                "Atendimento salvo, mas atenção: já existe outro atendimento para este animal nesta mesma data.",
                "error",
            )
        else:
            flash("Atendimento cadastrado com sucesso!", "success")

        return redirect(url_for("main.prontuario_animal", animal_id=animal.id))

    return render_template(
        "atendimento_novo.html",
        animal=animal,
        formulario=formulario,
        formularios_disponiveis=formularios_disponiveis,
        campos=campos,
        perfil_efetivo=perfil,
    )

@main.route("/atendimentos/<int:id>/editar", methods=["GET", "POST"])
@login_obrigatorio
@acesso_atendimento
def editar_atendimento(id):
    atendimento = Atendimento.query.get_or_404(id)
    animal = Animal.query.get_or_404(atendimento.animal_id)
    usuario = obter_usuario_logado()

    if atendimento.bloqueado_em and usuario.perfil not in ["admin_master", "veterinario"]:
        flash("Este atendimento está bloqueado e não pode ser editado.", "error")
        return redirect(url_for("main.prontuario_animal", animal_id=animal.id))

    formulario = atendimento.formulario
    campos = sorted(formulario.campos, key=lambda c: (c.ordem or 0, c.id)) if formulario else []

    if request.method == "POST":
        dados = {}
        erro = None

        data_atendimento_str = (request.form.get("data_atendimento") or "").strip()
        if not data_atendimento_str:
            flash("A data do atendimento é obrigatória.", "error")
            return redirect(request.url)

        try:
            data_atendimento = datetime.strptime(data_atendimento_str, "%Y-%m-%d").date()
        except ValueError:
            flash("Data do atendimento inválida.", "error")
            return redirect(request.url)

        atendimento_existente = (
            Atendimento.query
            .filter(
                Atendimento.animal_id == animal.id,
                Atendimento.data_atendimento == data_atendimento,
                Atendimento.id != atendimento.id,
            )
            .first()
        )
        duplicado_mesma_data = atendimento_existente is not None

        for campo in campos:
            valor = request.form.get(campo.nome_chave)

            if campo.tipo == "checkbox":
                valor = campo.nome_chave in request.form

            elif campo.tipo == "number":
                if valor not in (None, ""):
                    try:
                        valor = float(valor) if "." in valor else int(valor)
                    except ValueError:
                        erro = f"O campo '{campo.rotulo}' deve ser numérico."
                        break
                else:
                    valor = None

            elif campo.tipo == "date":
                if valor:
                    try:
                        datetime.strptime(valor, "%Y-%m-%d")
                    except ValueError:
                        erro = f"O campo '{campo.rotulo}' possui uma data inválida."
                        break
                else:
                    valor = None

            else:
                valor = (valor or "").strip() or None

            if campo.obrigatorio:
                vazio = (
                    valor is None
                    or valor == ""
                    or (campo.tipo == "checkbox" and valor is False)
                )
                if vazio:
                    erro = f"O campo '{campo.rotulo}' é obrigatório."
                    break

            dados[campo.nome_chave] = valor

        if erro:
            flash(erro, "error")
            return redirect(request.url)

        atendimento.dados = dados
        atendimento.data_atendimento = data_atendimento

        db.session.commit()

        imagens = request.files.getlist("imagens")
        for imagem in imagens:
            if imagem and imagem.filename:
                salvar_imagem_atendimento(atendimento.id, imagem)

        if duplicado_mesma_data:
            flash(
                "Atendimento atualizado, mas atenção: já existe outro atendimento para este animal nesta mesma data.",
                "error",
            )
        else:
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


@main.route("/atendimentos/<int:id>/excluir")
@login_obrigatorio
@acesso_atendimento
def excluir_atendimento(id):
    atendimento = Atendimento.query.get_or_404(id)
    usuario = obter_usuario_logado()
    animal_id = atendimento.animal_id

    if usuario.perfil not in ["admin_master", "veterinario"]:
        flash("Você não tem permissão para excluir atendimentos.", "error")
        return redirect(url_for("main.prontuario_animal", animal_id=animal_id))

    db.session.delete(atendimento)
    db.session.commit()

    flash("Atendimento excluído com sucesso.", "success")
    return redirect(url_for("main.prontuario_animal", animal_id=animal_id))


@main.route("/atendimentos/<int:id>/bloquear")
@login_obrigatorio
@acesso_atendimento
def bloquear_atendimento(id):
    atendimento = Atendimento.query.get_or_404(id)
    usuario = obter_usuario_logado()

    if usuario.perfil not in ["admin_master", "veterinario"]:
        flash("Você não tem permissão para bloquear atendimentos.", "error")
        return redirect(url_for("main.prontuario_animal", animal_id=atendimento.animal_id))

    atendimento.bloqueado_em = datetime.utcnow()
    db.session.commit()

    flash("Atendimento bloqueado com sucesso.", "success")
    return redirect(url_for("main.prontuario_animal", animal_id=atendimento.animal_id))


@main.route("/atendimentos/<int:id>/desbloquear")
@login_obrigatorio
@acesso_atendimento
def desbloquear_atendimento(id):
    atendimento = Atendimento.query.get_or_404(id)
    usuario = obter_usuario_logado()

    if usuario.perfil not in ["admin_master", "veterinario"]:
        flash("Você não tem permissão para desbloquear atendimentos.", "error")
        return redirect(url_for("main.prontuario_animal", animal_id=atendimento.animal_id))

    atendimento.bloqueado_em = None
    db.session.commit()

    flash("Atendimento desbloqueado com sucesso.", "success")
    return redirect(url_for("main.prontuario_animal", animal_id=atendimento.animal_id))


@main.route("/atendimentos/<int:id>/pdf")
@login_obrigatorio
@acesso_atendimento
def exportar_atendimento_pdf(id):
    atendimento = Atendimento.query.get_or_404(id)
    animal = Animal.query.get_or_404(atendimento.animal_id)

    return gerar_pdf_atendimento(atendimento, animal)


@main.route("/atendimentos/<int:id>/exames/novo", methods=["GET", "POST"])
@login_obrigatorio
@acesso_atendimento
def novo_exame(id):
    atendimento = Atendimento.query.get_or_404(id)

    if request.method == "POST":
        categoria = (request.form.get("categoria") or "").strip()
        nome_exame = (request.form.get("nome_exame") or "").strip()
        resultado = (request.form.get("resultado") or "").strip() or None
        observacoes = (request.form.get("observacoes") or "").strip() or None
        data_exame_str = (request.form.get("data_exame") or "").strip()

        if categoria not in ["laboratorial", "imagem"]:
            flash("Categoria inválida.", "error")
            return redirect(request.url)

        if not nome_exame:
            flash("O nome do exame é obrigatório.", "error")
            return redirect(request.url)

        data_exame = None
        if data_exame_str:
            try:
                data_exame = datetime.strptime(data_exame_str, "%Y-%m-%d").date()
            except ValueError:
                flash("Data do exame inválida.", "error")
                return redirect(request.url)

        arquivo = request.files.get("arquivo")
        caminho_arquivo = None

        if arquivo and arquivo.filename:
            caminho_arquivo = salvar_arquivo_exame(arquivo)

        exame = Exame(
            atendimento_id=atendimento.id,
            categoria=categoria,
            nome_exame=nome_exame,
            data_exame=data_exame,
            resultado=resultado,
            observacoes=observacoes,
            arquivo=caminho_arquivo,
        )

        db.session.add(exame)
        db.session.commit()

        flash("Exame cadastrado com sucesso.", "success")
        return redirect(url_for("main.prontuario_animal", animal_id=atendimento.animal_id))

    return render_template("exame_novo.html", atendimento=atendimento)