from order_vault.models.db import db
from datetime import datetime

class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String, unique=True, nullable=False)
    password_hash = db.Column(db.String, nullable=False)
    client_id = db.Column(db.String, nullable=False)  # e.g., "nike", "zara"
    api_key = db.Column(db.String(128), unique=True, nullable=True)
