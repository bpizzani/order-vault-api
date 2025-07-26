from order_vault.models.db import db
from datetime import datetime

class Evaluation(db.Model):
    __tablename__ = 'evaluations'
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.String, nullable=True)
    checkout_id = db.Column(db.String, nullable=True)
    visitor_id = db.Column(db.String, nullable=False)  # SHA256 = 64 hex chars
    local_storage_device = db.Column(db.String, nullable=True)
    risk_decision = db.Column(db.String, nullable=True)
    risk_features = db.Column(db.String, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
