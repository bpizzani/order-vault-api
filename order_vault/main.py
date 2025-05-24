import os
from flask import Flask
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from neo4j import GraphDatabase
from order_vault import app
from order_vault.models.db import db

# ─── Configuration (keep here) ─────────────────────────────────
# Flask App Setup
app.secret_key = "your_secret_key"
# Database configuration
app.config["SQLALCHEMY_DATABASE_URI"] = 'postgresql://u32cgla1pp9fm7:p6f656fa0f2edb9dda1653485f118f3b8379d957dce3469ef41d13f34d73e8cb1@c5flugvup2318r.cluster-czrs8kj4isg7.us-east-1.rds.amazonaws.com:5432/dc0evnfhnut69e' #os.getenv('DATABASE_URL') #os.environ.get("DATABASE_URL") #"sqlite:///orders_v4.db" #os.environ.get("DATABASE_URL", "sqlite:///orders_v4.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False


# ─── Initialize extensions ──────────────────────────────────────
print(f"Database URI: {os.getenv('DATABASE_URL')}")
db.init_app(app)
migrate = Migrate(app, db)  # Initialize Flask-Migrate with the app and db

#api = Api(app)
#db      = SQLAlchemy(app)
#migrate = Migrate(app, db)

CORS(app, supports_credentials=True)

driver = GraphDatabase.driver(
    os.getenv("NEO4J_URI", "neo4j+s://f34af65f.databases.neo4j.io") ,
    auth=(
        os.getenv("NEO4J_USER", "neo4j"),
        os.getenv("NEO4J_PASSWORD", "OPESlEPx3V4kYLSOo86X5fHX0k_HhKprCVG_erEfi7A")
    )
)

# ─── Register all Blueprints ────────────────────────────────────
from order_vault.routes.home        import home_bp
from order_vault.routes.fingerprint import fingerprint_bp
from order_vault.routes.orders      import orders_bp
from order_vault.routes.rules       import rules_bp
from order_vault.routes.evaluate    import evaluate_bp
from order_vault.routes.customer    import customer_bp
from order_vault.routes.promocode   import promocode_bp

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
    print("Start APP")
    #debug = os.getenv("FLASK_ENV", "development") != "production"
    #port  = int(os.getenv("PORT", 5000))
    #app.run(host="0.0.0.0", port=port, debug=debug)
