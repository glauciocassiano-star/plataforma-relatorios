from app import create_app, db, garantir_admin_master_padrao

print("🔄 Iniciando bootstrap do Render...")

app = create_app()

with app.app_context():
    db.create_all()
    garantir_admin_master_padrao()

print("✅ Bootstrap concluído com sucesso.")