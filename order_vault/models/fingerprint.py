from order_vault.models.db import db
from datetime import datetime

class FingerprintEvents(db.Model):
    __tablename__ = 'fingerprint_events'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(100), nullable=True)
    visitor_id = db.Column(db.String(64), nullable=False)  # SHA256 = 64 hex chars
    cookie_session = db.Column(db.String(64), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
