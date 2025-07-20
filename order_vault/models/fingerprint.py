from order_vault.models.db import db
from datetime import datetime

class FingerprintEvents(db.Model):
    __tablename__ = 'fingerprint_events'
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.String, nullable=True)
    visitor_id = db.Column(db.String, nullable=False)  # SHA256 = 64 hex chars
    js_visitor_id = db.Column(db.String, nullable=True)
    cookie_session = db.Column(db.String, nullable=True)
    local_storage_device = db.Column(db.String, nullable=True)
    user_agent =  db.Column(db.String, nullable=True)
    webdriver = db.Column(db.String, nullable=True)
    platform = db.Column(db.String, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
