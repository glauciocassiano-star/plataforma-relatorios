from datetime import datetime

from app import db
from app.models import Animal


def listar_animais_da_propriedade(propriedade_id):
    return (
        Animal.query
        .filter_by(propriedade_id=propriedade_id)
        .order_by(Animal.codigo.asc())
        .all()
    )


def criar_animal(dados, propriedade_id):
    # =========================
    # NORMALIZAÇÃO DOS DADOS
    # =========================
    codigo = (dados.get("codigo") or "").strip().upper()
    nome = (dados.get("nome") or "").strip() or None
    data_nascimento_str = (dados.get("data_nascimento") or "").strip()
    raca = (dados.get("raca") or "").strip() or None
    sexo = (dados.get("sexo") or "").strip() or None
    perfil_genetico = (dados.get("perfil_genetico") or "").strip() or None
    especie = (dados.get("especie") or "").strip().lower() or "bovino"

    # =========================
    # VALIDAÇÕES
    # =========================
    if not codigo:
        return None, "Código do animal é obrigatório."

    if not especie:
        return None, "Espécie é obrigatória."

    # =========================
    # DATA
    # =========================
    data_nascimento = None
    if data_nascimento_str:
        try:
            data_nascimento = datetime.strptime(
                data_nascimento_str, "%Y-%m-%d"
            ).date()
        except ValueError:
            return None, "Data de nascimento inválida."

    # =========================
    # DUPLICIDADE
    # =========================
    animal_existente = Animal.query.filter_by(
        codigo=codigo,
        propriedade_id=propriedade_id
    ).first()

    if animal_existente:
        return None, "Já existe um animal com esse código nesta propriedade."

    # =========================
    # CRIAÇÃO
    # =========================
    animal = Animal(
        codigo=codigo,
        nome=nome,
        data_nascimento=data_nascimento,
        raca=raca,
        sexo=sexo,
        perfil_genetico=perfil_genetico,
        especie=especie,
        propriedade_id=propriedade_id,
    )

    # =========================
    # PERSISTÊNCIA
    # =========================
    try:
        db.session.add(animal)
        db.session.commit()
    except Exception:
        db.session.rollback()
        return None, "Ocorreu um erro ao salvar o animal. Tente novamente."

    return animal, None