# pip install pyjwt flask-cors
from functools import wraps
from flask import request, g, jsonify, abort, current_app
from flask_cors import CORS
import jwt, time
from order_vault.models.tenant import Tenant
from order_vault.utils.crypto import enc, dec
from neo4j import GraphDatabase
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
 
# Tighten these to known origins in prod
#CORS(app, resources={r"/api/*": { #"origins": ["https://merchant.example.com"],
#                                 "allow_headers": ["Content-Type","Authorization","X-CLIENT-ID","X-API-KEY"],
#                                 "methods": ["POST","OPTIONS"]}})

# --- Use your real storage instead of hard-coded dicts ---
# Option A: HS256 shared secret per client (simple)
CLIENT_JWT_SECRETS = {
    "client_c": "shared-signing-secret-from-onboarding",
    "client_1": "shared-signing-secret-from-onboarding"
}

PUBLISHABLE_KEYS = {  # scoped to fingerprint-only
    "client_c": {"key": "abcde", "origins": ["https://order-vault-client-webapp-13ee822f0ba9.herokuapp.com"]},
    "client_1": {"key": "trial_abc", "origins": ["https://order-vault-client-webapp-13ee822f0ba9.herokuapp.com"]},

}

def _set_tenant_context(client_id):
    tenant = Tenant.query.filter_by(client_id=client_id).first()
    if not tenant:
        abort(401, description="unknown_tenant")
        
    pg_uri_dec = dec(tenant.pg_uri_enc)
    neo4j_uri_dec = dec(tenant.neo4j_uri_enc)
    neo4j_user_dec = dec(tenant.neo4j_user_enc)
    neo4j_pass_dec = dec(tenant.neo4j_pass_enc)
      
    g.client_id = client_id
    g.db_uri = pg_uri_dec
    g.neo4j_driver = GraphDatabase.driver(
        neo4j_uri_dec,
        auth=(neo4j_user_dec, neo4j_pass_dec)
    )

def _verify_api_key_or_401():
    api_key = request.headers.get("X-API-KEY")
    client_id_key = request.headers.get("X-CLIENT-ID")
    if not api_key or not client_id_key:
        abort(401, description="missing_api_key_or_client_id")
    user = User.query.filter_by(api_key=api_key, client_id=client_id_key).first()
    if not user:
        abort(401, description="invalid_api_key_or_client_id")
    g.user = user
    _set_tenant_context(user.client_id)
    g.auth_type = "api_key"

def _verify_bearer_or_401(scope_required: str = ""):
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        abort(401, description="missing_bearer")
    token = auth.split(" ", 1)[1]
    print(token)

    try:
        # Peek to decide which client secret to use
        unverified = jwt.decode(token, options={"verify_signature": False})
        cid = unverified.get("cid")
        secret = CLIENT_JWT_SECRETS.get(cid)
        if not cid or not secret:
            abort(401, description="unknown_client_for_token")

        claims = jwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            audience="rediim-api"
        )
        if "exp" in claims and claims["exp"] < time.time():
            abort(401, description="token_expired")

        scopes = claims.get("scope", [])
        if scope_required and scope_required not in scopes:
            abort(403, description="insufficient_scope")

        _set_tenant_context(cid)
        g.token_claims = claims
        g.auth_type = "bearer"
    except jwt.ExpiredSignatureError:
        abort(401, description="token_expired")
    except jwt.InvalidTokenError:
        abort(401, description="invalid_token")

def require_auth(scope: str = ""):
    """Accept Bearer (preferred for browsers) OR API key (servers)."""
    def deco(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            # Preflight pass-through
            if request.method == "OPTIONS":
                return "", 200
            auth = request.headers.get("Authorization", "")
            if auth.startswith("Bearer "):
                 print("BEARER!")
                _verify_bearer_or_401(scope)
            else:
                _verify_api_key_or_401()
            return fn(*args, **kwargs)
        return wrapper
    return deco


limiter = Limiter(get_remote_address, app=current_app, default_limits=["60/minute"])

def require_publishable_key(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        pk = request.headers.get("X-PUBLISHABLE-KEY")
        cid = request.headers.get("X-CLIENT-ID")
        print(pk)
        if not pk or not cid:
            return jsonify({"error":"missing_publishable_or_client_id"}), 401
        conf = PUBLISHABLE_KEYS.get(cid)
        if not conf or conf["key"] != pk:
            return jsonify({"error":"invalid_publishable_key"}), 401

        # (Optional) enforce origin
        #origin = request.headers.get("Origin")
        #if conf.get("origins") and origin not in conf["origins"]:
        #    return jsonify({"error":"origin_not_allowed"}), 403

        # (Optional) verify captcha token in body here

        # scope: only allow this decorator on fingerprint endpoints
        return fn(*args, **kwargs)
    return limiter.limit("30/minute")(wrapper)  # tighter per-endpoint limit
