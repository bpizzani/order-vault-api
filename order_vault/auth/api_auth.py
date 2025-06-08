from functools import wraps
from flask import request, g, jsonify
from order_vault.models.user import User
from order_vault.settings.tenants import TENANT_DATABASES
from neo4j import GraphDatabase

def require_api_key(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        api_key = request.headers.get("X-API-KEY")
        if not api_key:
            return jsonify({"error": "Missing API key"}), 401

        user = User.query.filter_by(api_key=api_key).first()
        if not user:
            return jsonify({"error": "Invalid API key"}), 401

        tenant = TENANT_DATABASES.get(user.client_id)
        if not tenant:
            return jsonify({"error": "Unknown tenant"}), 401

        # Inject into `g`
        g.user = user
        g.client_id = user.client_id
        g.db_uri = tenant["postgres"]
        g.neo4j_driver = GraphDatabase.driver(
            tenant["neo4j"]["uri"],
            auth=(tenant["neo4j"]["user"], tenant["neo4j"]["password"])
        )

        return func(*args, **kwargs)
    return wrapper
