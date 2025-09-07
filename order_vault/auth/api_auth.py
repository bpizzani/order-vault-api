from functools import wraps
from flask import request, g, jsonify
from order_vault.models.user import User
from order_vault.settings.tenants import TENANT_DATABASES
from order_vault.models.tenant import Tenant
from order_vault.utils.crypto import enc, dec
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

        
        #tenant = TENANT_DATABASES.get(user.client_id)
        tenant = Tenant.query.filter_by(client_id=user.client_id).first()
        if not tenant:
            return jsonify({"error": "Unknown tenant"}), 401
            
        pg_uri_dec = dec(tenant.pg_uri_enc)
        neo4j_uri_dec = dec(tenant.neo4j_uri_enc)
        neo4j_user_dec = dec(tenant.neo4j_user_enc)
        neo4j_pass_dec = dec(tenant.neo4j_pass_enc)

        # Inject into `g`
        g.user = user
        g.client_id = user.client_id
        g.db_uri = pg_uri_dec
        g.neo4j_driver = GraphDatabase.driver(
            neo4j_uri_dec,
            auth=(neo4j_user_dec, neo4j_pass_dec)
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

        #tenant = TENANT_DATABASES.get(user.client_id)
        tenant = Tenant.query.filter_by(client_id=user.client_id).first()
        if not tenant:
            return jsonify({"error": "Unknown tenant"}), 401

        pg_uri_dec = dec(tenant.pg_uri_enc)
        neo4j_uri_dec = dec(tenant.neo4j_uri_enc)
        neo4j_user_dec = dec(tenant.neo4j_user_enc)
        neo4j_pass_dec = dec(tenant.neo4j_pass_enc)

        # Inject into `g`
        g.user = user
        g.client_id = user.client_id
        g.db_uri = pg_uri_dec
        g.neo4j_driver = GraphDatabase.driver(
            neo4j_uri_dec,
            auth=(neo4j_user_dec, neo4j_pass_dec)
        )

        return func(*args, **kwargs)
    return wrapper
