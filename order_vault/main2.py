import os
from flask import Flask
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from neo4j import GraphDatabase

# ─── Configuration (keep here) ─────────────────────────────────
app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = os.getenv("SECRET_KEY", "your_secret_key")

app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
    "DATABASE_URL",
    "postgresql://...your_rds_uri..."
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# ─── Initialize extensions ──────────────────────────────────────
db      = SQLAlchemy(app)
migrate = Migrate(app, db)
CORS(app, supports_credentials=True)

driver = GraphDatabase.driver(
    os.getenv("NEO4J_URI", "neo4j+s://...") ,
    auth=(
        os.getenv("NEO4J_USER", "neo4j"),
        os.getenv("NEO4J_PASSWORD", "")
    )
)

# ─── Register all Blueprints ────────────────────────────────────
from routes.home        import home_bp
from routes.fingerprint import fingerprint_bp
from routes.orders      import orders_bp
from routes.rules       import rules_bp
from routes.evaluate    import evaluate_bp
from routes.customer    import customer_bp
from routes.promocode   import promocode_bp

for bp in (
    home_bp,
    fingerprint_bp,
    orders_bp,
    rules_bp,
    evaluate_bp,
    customer_bp,
    promocode_bp
):
    app.register_blueprint(bp)

# ─── Run ────────────────────────────────────────────────────────
if __name__ == "__main__":
    debug = os.getenv("FLASK_ENV", "development") != "production"
    port  = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=debug)
