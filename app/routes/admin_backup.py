import os
import zipfile
from datetime import datetime

from flask import flash, redirect, render_template, send_from_directory, url_for

from .base import main
from ..helpers.decorators import login_obrigatorio, admin_obrigatorio


def obter_pasta_backups():
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    pasta_backups = os.path.join(base_dir, "backups")
    os.makedirs(pasta_backups, exist_ok=True)
    return pasta_backups


def gerar_backup_zip():
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    pasta_instance = os.path.join(base_dir, "instance")
    pasta_backups = obter_pasta_backups()

    caminho_banco = os.path.join(pasta_instance, "database.db")

    if not os.path.exists(caminho_banco):
        raise FileNotFoundError("Banco de dados não encontrado em instance/database.db.")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    nome_zip = f"backup_{timestamp}.zip"
    caminho_zip = os.path.join(pasta_backups, nome_zip)

    with zipfile.ZipFile(caminho_zip, "w", zipfile.ZIP_DEFLATED) as zipf:
        zipf.write(caminho_banco, arcname="database.db")

    return nome_zip


def listar_backups():
    pasta_backups = obter_pasta_backups()
    arquivos = []

    for nome in os.listdir(pasta_backups):
        if not nome.endswith(".zip"):
            continue

        caminho = os.path.join(pasta_backups, nome)

        if not os.path.isfile(caminho):
            continue

        stat = os.stat(caminho)

        arquivos.append({
            "nome": nome,
            "tamanho_bytes": stat.st_size,
            "tamanho_mb": round(stat.st_size / (1024 * 1024), 2),
            "modificado_em": datetime.fromtimestamp(stat.st_mtime),
        })

    arquivos.sort(key=lambda x: x["modificado_em"], reverse=True)
    return arquivos


@main.route("/admin/backup")
@login_obrigatorio
@admin_obrigatorio
def admin_backup():
    backups = listar_backups()

    return render_template(
        "admin_backup.html",
        backups=backups,
    )


@main.route("/admin/backup/gerar", methods=["POST"])
@login_obrigatorio
@admin_obrigatorio
def gerar_backup():
    try:
        nome_arquivo = gerar_backup_zip()
        flash(f"Backup gerado com sucesso: {nome_arquivo}", "success")
    except Exception as e:
        flash(f"Erro ao gerar backup: {str(e)}", "error")

    return redirect(url_for("main.admin_backup"))


@main.route("/admin/backup/download/<path:nome_arquivo>")
@login_obrigatorio
@admin_obrigatorio
def baixar_backup(nome_arquivo):
    pasta_backups = obter_pasta_backups()
    caminho_arquivo = os.path.join(pasta_backups, nome_arquivo)

    if not os.path.isfile(caminho_arquivo) or not nome_arquivo.endswith(".zip"):
        flash("Arquivo de backup não encontrado.", "error")
        return redirect(url_for("main.admin_backup"))

    return send_from_directory(
        pasta_backups,
        nome_arquivo,
        as_attachment=True,
    )


@main.route("/admin/backup/excluir/<path:nome_arquivo>", methods=["POST"])
@login_obrigatorio
@admin_obrigatorio
def excluir_backup(nome_arquivo):
    pasta_backups = obter_pasta_backups()
    caminho_arquivo = os.path.join(pasta_backups, nome_arquivo)

    if not os.path.isfile(caminho_arquivo) or not nome_arquivo.endswith(".zip"):
        flash("Arquivo de backup não encontrado.", "error")
        return redirect(url_for("main.admin_backup"))

    try:
        os.remove(caminho_arquivo)
        flash(f"Backup excluído com sucesso: {nome_arquivo}", "success")
    except Exception as e:
        flash(f"Erro ao excluir backup: {str(e)}", "error")

    return redirect(url_for("main.admin_backup"))