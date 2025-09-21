# pip install pyjwt flask-cors
from functools import wraps
from flask import request, g, jsonify, abort, current_app
from flask_cors import CORS
import jwt, time
from order_vault.models.user import User
from order_vault.models.tenant import Tenant
from order_vault.utils.crypto import enc, dec
from neo4j import GraphDatabase
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

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
    print("API!")
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


def _verify_publishable_key_or_401():
    print("PUBLISHING!")
    publishable_key = request.headers.get("X-PUBLISHABLE-KEY")
    client_id_key = request.headers.get("X-CLIENT-ID")
    origin = request.headers.get("Origin")
    print(origin)
    if not publishable_key or not client_id_key:
        abort(401, description="missing_publishable_key_or_client_id")
  
    user = User.query.filter_by(pk_key=publishable_key, client_id=client_id_key).first()
    if not user:
        abort(401, description="invalid_publishable_key_or_client_id")

    publishable_origins = user.pk_origin
    if origin and origin not in publishable_origins:
        return jsonify({"error":"origin_not_allowed"}), 403
     
    g.user = user
    _set_tenant_context(user.client_id)
    g.auth_type = "publishable"

def _verify_bearer_or_401(scope_required: str = ""):
    print("BEARER!")
    print(request.headers.get("Origin"))
    auth = request.headers.get("Authorization", "")
    x_client_id = request.headers.get("X-CLIENT-ID", "")
    
    if not auth.startswith("Bearer "):
        abort(401, description="missing_bearer")
    token = auth.split(" ", 1)[1]

    try:
        # Peek to decide which client secret to use
        unverified = jwt.decode(token, options={"verify_signature": False})
        cid = unverified.get("cid")
     
        user = User.query.filter_by(client_id=cid).first()
        if not user:
            abort(402, description="unknown_client_for_token")
            
        if x_client_id != cid:
            abort(404, description="client_id_not_matching_with_client_found")
         
        secret = user.jwt_secrets
        claims = jwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            audience="rediim-api"
        )
        if "exp" in claims and claims["exp"] < time.time():
            abort(405, description="token_expired")

        scopes = claims.get("scope", [])
        if scope_required and scope_required not in scopes:
            abort(406, description="insufficient_scope")

        _set_tenant_context(cid)
        g.token_claims = claims
        g.auth_type = "bearer"
    except jwt.ExpiredSignatureError:
        abort(407, description="token_expired")
    except jwt.InvalidTokenError as e:
        print("[AUTH] InvalidTokenError:", repr(e))
        abort(408, description="invalid_token")

def require_auth(scope: str = ""):
    """Accept Bearer (preferred for browsers) OR API key (servers)."""
    def deco(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            # Preflight pass-through
            if request.method == "OPTIONS":
                return "", 200
            auth = request.headers.get("Authorization", "")
            publishKey = request.headers.get("X-PUBLISHABLE-KEY", "")
            api_key = request.headers.get("X-API-KEY", "")
            
            if (publishKey != "") and (auth != "") and (publishKey != None) and (auth != None):
                try:
                    _verify_publishable_key_or_401()
                except:
                    print("PUBLISHABLE FAILED")
                    _verify_bearer_or_401(scope)
            elif (api_key != "") and (auth != "") and (auth != None) and (api_key != None):
                try:
                    _verify_bearer_or_401(scope)
                except:
                    print("BEARER FAILED")
                    _verify_api_key_or_401()
            elif auth.startswith("Bearer "):
                _verify_bearer_or_401(scope)
            elif (publishKey != None) and (publishKey != ""):
                 _verify_publishable_key_or_401()
            else:
                 _verify_api_key_or_401()
            return fn(*args, **kwargs)
        return wrapper
    return deco



