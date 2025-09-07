from functools import wraps
from flask import session, redirect, url_for, g
from order_vault.models.user import User
from order_vault.models.client_subscription import ClientSubscription
from order_vault.settings.tenants import TENANT_DATABASES
from order_vault.models.tenant import Tenant
from order_vault.utils.crypto import enc, dec
from neo4j import GraphDatabase

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = session.get("user_id")
        if not user_id:
            return redirect(url_for("auth.login"))  # Redirect to home if not logged in

        user = User.query.get(user_id)
        if not user:
            return redirect(url_for("auth.login"))

        #tenant = TENANT_DATABASES.get(user.client_id)
        tenant = Tenant.query.filter_by(client_id=user.client_id).first()
        if not tenant:
            return "Invalid tenant", 403

        pg_uri_dec = dec(tenant.pg_uri_enc)
        neo4j_uri_dec = dec(tenant.neo4j_uri_enc)
        neo4j_user_dec = dec(tenant.neo4j_user_enc)
        neo4j_pass_dec = dec(tenant.neo4j_pass_enc)

        subscription = ClientSubscription.query.filter_by(client_id=user.client_id).first()

        g.user = user
        g.client_id = user.client_id
        g.subscription_type = subscription.type
        g.db_uri = pg_uri_dec
        g.neo4j_driver = GraphDatabase.driver(
            neo4j_uri_dec,
            auth=(neo4j_user_dec, neo4j_pass_dec)
        )
        return f(*args, **kwargs)
    return decorated_function


# Option A: very specific gate for your case
def require_not_fingerprint_demo(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        sub_type = getattr(g, "subscription_type", None)
        if sub_type == "fingerprint_demo":
            # Choose your behavior: 403 or redirect somewhere permissible
            return redirect(url_for("home.fingerprint_ui"))
        return f(*args, **kwargs)
    return wrapper


# Option B: generic gate you can reuse for other plans
def require_subscription_in(*allowed_types):
    """
    Allow access only if g.subscription_type is in allowed_types.
    Example: @require_subscription_in("pro", "enterprise")
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            sub_type = getattr(g, "subscription_type", None)
            if sub_type not in allowed_types:
                return redirect(url_for("home.fingerprint_ui"))
            return f(*args, **kwargs)
        return wrapper
    return decorator
