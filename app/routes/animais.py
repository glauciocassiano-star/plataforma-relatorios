from datetime import datetime

from flask import flash, redirect, render_template, request, url_for

from .base import main
from .. import db
from ..helpers.decorators import (
    login_obrigatorio,
    acesso_propriedade,
    acesso_animal,
)
from ..models import Animal, Atendimento, Propriedade
from ..services.animal_service import criar_animal, listar_animais_da_propriedade


@main.route("/propriedades/<int:propriedade_id>/animais")
@login_obrigatorio
@acesso_propriedade
def listar_animais(propriedade_id):
    propriedade = Propriedade.query.get_or_404(propriedade_id)
    animais = listar_animais_da_propriedade(propriedade_id)

    return render_template(
        "animais.html",
        propriedade=propriedade,
        animais=animais,
    )


@main.route("/propriedades/<int:propriedade_id>/animais/novo", methods=["GET", "POST"])
@login_obrigatorio
@acesso_propriedade
def novo_animal(propriedade_id: int):
    propriedade = Propriedade.query.get_or_404(propriedade_id)

    if request.method == "POST":
        animal, erro = criar_animal(request.form, propriedade.id)

        if erro:
            flash(erro, "error")
            return redirect(request.url)

        flash("Animal cadastrado com sucesso!", "success")
        return redirect(url_for("main.listar_animais", propriedade_id=propriedade.id))

    return render_template("animal_novo.html", propriedade=propriedade)


@main.route("/animais/<int:animal_id>/editar", methods=["GET", "POST"])
@login_obrigatorio
@acesso_animal
def editar_animal(animal_id):
    animal = Animal.query.get_or_404(animal_id)
    propriedade = Propriedade.query.get_or_404(animal.propriedade_id)

    if request.method == "POST":
        codigo = (request.form.get("codigo") or "").strip()
        nome = (request.form.get("nome") or "").strip() or None
        especie = (request.form.get("especie") or "").strip() or "bovino"
        raca = (request.form.get("raca") or "").strip() or None
        sexo = (request.form.get("sexo") or "").strip() or None
        perfil_genetico = (request.form.get("perfil_genetico") or "").strip() or None
        data_nascimento = (request.form.get("data_nascimento") or "").strip()

        if not codigo:
            flash("O código do animal é obrigatório.", "error")
            return redirect(request.url)

        animal_existente = (
            Animal.query
            .filter(
                Animal.propriedade_id == propriedade.id,
                Animal.codigo == codigo,
                Animal.id != animal.id
            )
            .first()
        )

        if animal_existente:
            flash("Já existe outro animal com esse código nesta propriedade.", "error")
            return redirect(request.url)

        animal.codigo = codigo
        animal.nome = nome
        animal.especie = especie
        animal.raca = raca
        animal.sexo = sexo
        animal.perfil_genetico = perfil_genetico

        if data_nascimento:
            try:
                animal.data_nascimento = datetime.strptime(
                    data_nascimento, "%Y-%m-%d"
                ).date()
            except ValueError:
                flash("Data de nascimento inválida.", "error")
                return redirect(request.url)
        else:
            animal.data_nascimento = None

        db.session.commit()

        flash("Animal atualizado com sucesso.", "success")
        return redirect(url_for("main.listar_animais", propriedade_id=propriedade.id))

    return render_template(
        "animal_editar.html",
        animal=animal,
        propriedade=propriedade,
    )


@main.route("/animais/<int:animal_id>/excluir")
@login_obrigatorio
@acesso_animal
def excluir_animal(animal_id):
    animal = Animal.query.get_or_404(animal_id)
    propriedade_id = animal.propriedade_id

    atendimentos = Atendimento.query.filter_by(animal_id=animal.id).count()

    if atendimentos > 0:
        flash(
            "Não é possível excluir o animal porque existem atendimentos vinculados.",
            "error",
        )
        return redirect(url_for("main.listar_animais", propriedade_id=propriedade_id))

    db.session.delete(animal)
    db.session.commit()

    flash("Animal excluído com sucesso.", "success")
    return redirect(url_for("main.listar_animais", propriedade_id=propriedade_id))


@main.route("/animais/<int:animal_id>")
@login_obrigatorio
@acesso_animal
def prontuario_animal(animal_id: int):
    animal = Animal.query.get_or_404(animal_id)

    atendimentos = (
        Atendimento.query
        .filter_by(animal_id=animal.id)
        .order_by(Atendimento.data_atendimento.desc(), Atendimento.criado_em.desc())
        .all()
    )

    return render_template(
        "animal_prontuario.html",
        animal=animal,
        atendimentos=atendimentos,
    )