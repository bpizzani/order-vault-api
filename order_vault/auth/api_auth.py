from functools import wraps
from flask import request, g, jsonify
from order_vault.models.user import User
from order_vault.settings.tenants import TENANT_DATABASES
from neo4j import GraphDatabase

def require_api_key(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        api_key = request.headers.get("X-API-KEY")
        client_id_key = request.headers.get("X-CLIENT-ID")
        if not api_key:
            return jsonify({"error": "Missing API key"}), 401

        user = User.query.filter_by(api_key=api_key, client_id=client_id_key).first()
        if not user:
            return jsonify({"error": "Invalid API key"}), 401

        tenant = TENANT_DATABASES.get(user.client_id)
        if not tenant:
            return jsonify({"error": "Unknown tenant"}), 401

        # Inject into `g`
        g.user = user
        g.client_id = user.client_id
        g.db_uri = tenant["postgres_uri"]
        g.neo4j_driver = GraphDatabase.driver(
            tenant["neo4j_uri"],
            auth=(tenant["neo4j_user"], tenant["neo4j_password"])
        )

        return func(*args, **kwargs)
    return wrapper

def require_api_key_fingerprint(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if request.method == "OPTIONS":
            return "", 200  # Allow CORS preflight

        api_key = request.headers.get("X-API-KEY")
        client_id_key = request.headers.get("X-CLIENT-ID")
        #fingerprint_user_identifier_client = request.headers.get("user_identifier_client")

        if not api_key or not client_id_key:
            return jsonify({"error": "Missing API key or client ID"}), 401

        user = User.query.filter_by(api_key=api_key, client_id=client_id_key).first()
        if not user:
            return jsonify({"error": "Invalid API key or client ID"}), 401

        tenant = TENANT_DATABASES.get(user.client_id)
        if not tenant:
            return jsonify({"error": "Unknown tenant"}), 401

        #g.fingerprint_user_identifier_client = fingerprint_user_identifier_client
        g.user = user
        g.client_id = user.client_id
        g.db_uri = tenant["postgres_uri"]
        g.neo4j_driver = GraphDatabase.driver(
            tenant["neo4j_uri"],
            auth=(tenant["neo4j_user"], tenant["neo4j_password"])
        )

        return func(*args, **kwargs)
    return wrapper
