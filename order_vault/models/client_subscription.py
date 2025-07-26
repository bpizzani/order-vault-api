from order_vault.models.db import db
from datetime import datetime

class ClientSubscription(db.Model):
    __tablename__ = "client_subscriptions"

    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.String, nullable=False)
    type = db.Column(db.String, nullable=False)
    subscription_start = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    subscription_end = db.Column(db.DateTime, nullable=False)
    max_api_calls = db.Column(db.Integer, nullable=False)
    #api_calls_made = db.Column(db.Integer, default=0, nullable=True)

    def __repr__(self):
        return f"<ClientSubscription client_id={self.client_id} start={self.subscription_start} end={self.subscription_end} max_api_calls={self.max_api_calls}>"
