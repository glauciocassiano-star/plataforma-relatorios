from app import create_app, db, garantir_admin_master_padrao

print("🔄 Iniciando bootstrap do Render...")

app = create_app()

with app.app_context():
    print("🔄 Criando/atualizando estrutura do banco...")
    db.create_all()

    print("🔐 Garantindo existência do administrador master...")
    garantir_admin_master_padrao()

    print("✅ Bootstrap concluído com sucesso.")