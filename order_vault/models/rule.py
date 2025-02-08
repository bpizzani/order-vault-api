from order_vault.models.db import db
from datetime import datetime

class Rule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    attribute = db.Column(db.String(50), nullable=False)
    threshold = db.Column(db.Integer, nullable=False)
