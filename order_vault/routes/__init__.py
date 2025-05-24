from .fingerprint import fingerprint_bp
from .orders      import orders_bp
from .rules       import rules_bp
from .evaluate    import evaluate_bp
from .customer    import customer_bp
from .promocode   import promocode_bp

def register_blueprints(app):
    for bp in (fingerprint_bp, orders_bp, rules_bp,
               evaluate_bp, customer_bp, promocode_bp):
        app.register_blueprint(bp)
