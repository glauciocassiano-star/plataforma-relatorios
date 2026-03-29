from io import BytesIO

from flask import send_file
from weasyprint import HTML


def gerar_pdf_atendimento(atendimento, animal):
    data_atendimento = (
        atendimento.data_atendimento.strftime("%d/%m/%Y")
        if atendimento.data_atendimento else "-"
    )

    criado_em = (
        atendimento.criado_em.strftime("%d/%m/%Y às %H:%M")
        if atendimento.criado_em else "-"
    )

    itens_dados = ""
    if atendimento.dados:
        for chave, valor in atendimento.dados.items():
            valor_formatado = valor if valor not in [None, ""] else "-"
            itens_dados += f"""
            <tr>
                <td><strong>{chave}</strong></td>
                <td>{valor_formatado}</td>
            </tr>
            """
    else:
        itens_dados = """
        <tr>
            <td colspan="2">Sem dados registrados.</td>
        </tr>
        """

    html = f"""
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{
                font-family: Arial, sans-serif;
                font-size: 12px;
                color: #1f2937;
                margin: 30px;
            }}
            h1, h2 {{
                color: #1f8774;
                margin-bottom: 8px;
            }}
            .bloco {{
                border: 1px solid #d1d5db;
                border-radius: 10px;
                padding: 14px;
                margin-bottom: 18px;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 10px;
            }}
            th, td {{
                border: 1px solid #e5e7eb;
                padding: 8px;
                text-align: left;
                vertical-align: top;
            }}
            th {{
                background: #f9fafb;
            }}
        </style>
    </head>
    <body>
        <h1>Relatório de Atendimento</h1>

        <div class="bloco">
            <h2>Animal</h2>
            <p><strong>Código:</strong> {animal.codigo}</p>
            <p><strong>Nome:</strong> {animal.nome or "-"}</p>
            <p><strong>Espécie:</strong> {animal.especie or "-"}</p>
            <p><strong>Raça:</strong> {animal.raca or "-"}</p>
            <p><strong>Sexo:</strong> {animal.sexo or "-"}</p>
        </div>

        <div class="bloco">
            <h2>Atendimento</h2>
            <p><strong>Data do atendimento:</strong> {data_atendimento}</p>
            <p><strong>Registrado em:</strong> {criado_em}</p>
            <p><strong>ID:</strong> {atendimento.id}</p>
        </div>

        <div class="bloco">
            <h2>Dados do atendimento</h2>
            <table>
                <thead>
                    <tr>
                        <th>Campo</th>
                        <th>Valor</th>
                    </tr>
                </thead>
                <tbody>
                    {itens_dados}
                </tbody>
            </table>
        </div>
    </body>
    </html>
    """

    pdf_bytes = HTML(string=html).write_pdf()
    buffer = BytesIO(pdf_bytes)
    buffer.seek(0)

    nome_arquivo = f"atendimento_{animal.codigo}_{atendimento.id}.pdf"

    return send_file(
        buffer,
        as_attachment=True,
        download_name=nome_arquivo,
        mimetype="application/pdf",
    )