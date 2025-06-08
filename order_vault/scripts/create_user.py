from order_vault import app
from order_vault.models.db import db
from order_vault.models.user import User
from werkzeug.security import generate_password_hash

def create_user(email, password, client_id):
    with app.app_context():
        hashed_pw = generate_password_hash(password)
        user = User(email=email.lower(), password_hash=hashed_pw, client_id=client_id)
        db.session.add(user)
        db.session.commit()
        print(f"✅ Created user: {email} (client_id: {client_id})")

if __name__ == "__main__":
    # Example usage
    create_user("client_a@example.com", "my_secure_password", "client_a")
