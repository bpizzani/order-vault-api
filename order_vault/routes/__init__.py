from .fingerprint import bp as fingerprint_bp
from .orders      import bp as orders_bp
from .rules       import bp as rules_bp
from .evaluate    import bp as evaluate_bp
from .customer    import bp as customer_bp
from .promocode   import bp as promocode_bp

def register_blueprints(app):
    for bp in (fingerprint_bp, orders_bp, rules_bp,
               evaluate_bp, customer_bp, promocode_bp):
        app.register_blueprint(bp)
