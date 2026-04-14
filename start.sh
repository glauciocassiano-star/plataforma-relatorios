from app import create_app, db

app = create_app()

with app.app_context():
    print("🔄 Criando/atualizando tabelas...")
    db.create_all()
    print("✅ Banco de dados atualizado com sucesso!")