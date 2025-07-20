from order_vault.models.db import db
from datetime import datetime

class Rule(db.Model):
    __tablename__ = 'rule'
    id = db.Column(db.Integer, primary_key=True)
    attribute = db.Column(db.String(50), nullable=False)
    threshold = db.Column(db.Integer, nullable=False)
    promocode = db.Column(db.String(100), nullable=True)
    client_id = db.Column(db.String, nullable=False)

