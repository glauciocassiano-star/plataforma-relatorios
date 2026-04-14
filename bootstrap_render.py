from run import app
from app import db, garantir_admin_master_padrao

print("🔄 Iniciando bootstrap do Render...")

with app.app_context():
    print("⚠️ Removendo estrutura antiga do banco...")
    db.drop_all()

    print("✅ Criando estrutura nova do banco...")
    db.create_all()

    garantir_admin_master_padrao()
    print("✅ Admin master garantido com sucesso.")
