from order_vault.models.db import db
from datetime import datetime

class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String, unique=True, nullable=False)
    password_hash = db.Column(db.String, nullable=False)
    client_id = db.Column(db.String, nullable=False)
    api_key = db.Column(db.String(128), unique=False, nullable=True)
    pk_key = db.Column(db.String(128), unique=False, nullable=True)
    pk_origin = db.Column(JSON, nullable=True)
    jwt_secrets = db.Column(db.String(128), unique=False, nullable=True)
