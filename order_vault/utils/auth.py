from functools import wraps
from flask import session, redirect, url_for, g
from order_vault.models.user import User
from order_vault.settings.tenants import TENANT_DATABASES
from neo4j import GraphDatabase

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = session.get("user_id")
        if not user_id:
            return redirect(url_for("home.home"))  # Redirect to home if not logged in

        user = User.query.get(user_id)
        if not user:
            return redirect(url_for("home.home"))

        tenant = TENANT_DATABASES.get(user.client_id)
        if not tenant:
            return "Invalid tenant", 403

        g.user = user
        g.client_id = user.client_id
        g.db_uri = tenant["postgres_uri"]
        g.neo4j_driver = GraphDatabase.driver(
            tenant["neo4j_uri"],
            auth=(tenant["neo4j_user"], tenant["neo4j_password"])
        )
        return f(*args, **kwargs)
    return decorated_function
