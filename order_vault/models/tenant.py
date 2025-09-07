# models/tenant.py
from order_vault.models.db import db

class Tenant(db.Model):
    __tablename__ = "tenants"
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.String(120), unique=True, nullable=False, index=True)

    # store ciphertext, not plaintext
    pg_uri_enc = db.Column(db.LargeBinary, nullable=False)
    neo4j_uri_enc = db.Column(db.LargeBinary, nullable=False)
    neo4j_user_enc = db.Column(db.LargeBinary, nullable=False)
    neo4j_pass_enc = db.Column(db.LargeBinary, nullable=False)

    # optional: metadata
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())
