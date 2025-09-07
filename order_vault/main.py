import os
from flask import Flask, g, current_app
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from order_vault.models.db import db
from order_vault.auth.sessions import load_tenant_from_session
from order_vault import app
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from order_vault.models.tenant import Tenant
from order_vault.utils.crypto import enc, dec

# --- Define key function
def get_client_id():
    return getattr(g, "client_id", get_remote_address())  # fallback to IP


# ─── Flask App Setup ─────────────────────────────
app.secret_key = "your_secret_key"
app.config["SESSION_COOKIE_DOMAIN"] = ".rediim.com"
#app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
#app.config["SESSION_COOKIE_SECURE"] = True  # Only for HTTPS

# ─── Shared PostgreSQL DB (Auth & User Table) ────
app.config["SQLALCHEMY_DATABASE_URI"] = current_app.config.get("SQLALCHEMY_DATABASE_URI")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# ─── Initialize Extensions ───────────────────────
db.init_app(app)
migrate = Migrate(app, db)
CORS(app, supports_credentials=True)


@app.before_request
def before_request():
    load_tenant_from_session()

@app.context_processor
def inject_globals():
    return {"client_id": getattr(g, "client_id", None), 
            "client_email": getattr(g, "client_email", None),
            "subscription_type": getattr(g, "subscription_type", None)}

# --- Initialize limiter
limiter = Limiter(
    key_func=get_client_id,
    app=app,
    default_limits=["500 per day", "100 per hour"],  # Optional global limits
)
        
# ─── Register Blueprints ─────────────────────────
from order_vault.routes.home import home_bp
from order_vault.routes.fingerprint import fingerprint_bp
from order_vault.routes.orders import orders_bp
from order_vault.routes.rules import rules_bp
from order_vault.routes.evaluate import evaluate_bp
from order_vault.routes.customer import customer_bp
from order_vault.routes.promocode import promocode_bp
from order_vault.auth.routes import auth_bp  # <== ADD THIS

for bp in (
    auth_bp,  # <== Add auth route first
    home_bp,
    fingerprint_bp,
    orders_bp,
    rules_bp,
    evaluate_bp,
    customer_bp,
    promocode_bp
):
    app.register_blueprint(bp)

# ─── Run App ─────────────────────────────────────
if __name__ == "__main__":
    print("Start APP")
    #app.run(debug=True)
