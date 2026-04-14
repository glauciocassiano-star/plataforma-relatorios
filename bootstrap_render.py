from app import create_app, db, garantir_admin_master_padrao

print("🔄 Iniciando bootstrap do Render...")

app = create_app()

with app.app_context():
    print("⚠️ Removendo estrutura antiga do banco...")
    db.drop_all()

    print("✅ Criando estrutura nova do banco...")
    db.create_all()

    garantir_admin_master_padrao()
    print("✅ Admin master garantido com sucesso.")