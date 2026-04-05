from run import app
from app import db
from app.models import Usuario
from werkzeug.security import generate_password_hash

print("🔄 Iniciando bootstrap do Render...")

with app.app_context():
    db.create_all()
    print("✅ Tabelas verificadas/criadas com sucesso.")

    email_admin = "glaucio.cassiano@gmail.com"
    admin_existente = Usuario.query.filter_by(email=email_admin).first()

    if not admin_existente:
        admin = Usuario(
            nome="Administrador Master",
            email=email_admin,
            senha_hash=generate_password_hash("159951baB="),
            perfil="admin_master",
            ativo=True
        )
        db.session.add(admin)
        db.session.commit()
        print("✅ Admin master criado com sucesso.")
    else:
        print("ℹ️ Admin master já existe.")