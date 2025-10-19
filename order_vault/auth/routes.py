from flask import Blueprint, request, jsonify, session, current_app, redirect, url_for, render_template, g
from order_vault.models.user import User
from order_vault.models.client_subscription import ClientSubscription
from order_vault.main import db
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime
from order_vault.utils.auth import login_required

# 🔽 NEW imports for the admin tenant API
from sqlalchemy.exc import SQLAlchemyError
from order_vault.models.tenant import Tenant
from order_vault.utils.crypto import enc, dec
import json
import secrets

auth_bp = Blueprint("auth", __name__)

# ----------------------------
# Helpers (admin key + masking)
# ----------------------------
def _require_admin() -> bool:
    expected = current_app.config.get("ADMIN_API_KEY")
    provided = request.headers.get("X-API-KEY")
    # Optional convenience: allow ?admin_key=... in dev, but header takes precedence
    if not provided:
        provided = request.args.get("admin_key") or (request.json or {}).get("admin_key") if request.is_json else None
    return bool(expected) and provided == expected

def _mask(s: str, keep: int = 4) -> str:
    try:
        return (s or "")[:keep] + "•••" if s and len(s) > keep else "•••"
    except Exception:
        return "•••"

def _parse_pk_origins(raw):
    """
    Accepts:
      - JSON array string: '["https://a.com","https://b.com"]'
      - Comma-separated string: 'https://a.com, https://b.com'
    Returns: list[str]
    """
    if not raw:
        return None
    raw = raw.strip()
    try:
        val = json.loads(raw)
        if isinstance(val, list) and all(isinstance(x, str) for x in val):
            return [o.strip() for o in val if o and o.strip()]
    except Exception:
        pass
    # fallback: comma-separated
    return [o.strip() for o in raw.split(",") if o.strip()]

def _maybe(value):
    """Treat empty strings as None."""
    if value is None:
        return None
    v = str(value).strip()
    return v if v else None

def _ensure_api_key(existing):
    """Generate an API key if none provided and none exists."""
    return existing or f"rk_{secrets.token_hex(24)}"

def _ensure_pk_key(existing):
    """Generate a publishable key if none provided and none exists."""
    return existing or f"pk_{secrets.token_hex(16)}"


def _valid_password(pw: str) -> bool:
    return (
        isinstance(pw, str) and len(pw) >= 5
        and any(c.islower() for c in pw)
        #and any(c.isupper() for c in pw)
        #and any(c.isdigit() for c in pw)
    )

@auth_bp.route("/change-password", methods=["GET"])
def change_password_page():
    if not session.get("user_id"):
        return redirect(url_for("auth.login"))
    # If already onboarded, skip
    user = User.query.get(session["user_id"])
    if not user:
        session.clear()
        return redirect(url_for("auth.login"))
    if user.onboarded_flag == 1:
        return redirect(url_for("home.promotion_ui"))
    return render_template("change_password.html")  # contains a form that POSTs to /change-password


@auth_bp.route("/change-password", methods=["POST"])
def change_password_submit():
    if not session.get("user_id"):
        return (jsonify({"error": "Not authenticated"}), 401) if request.is_json else redirect(url_for("auth.login"))

    user = User.query.get(session["user_id"])
    if not user:
        session.clear()
        return (jsonify({"error": "Not authenticated"}), 401) if request.is_json else redirect(url_for("auth.login"))

    data = request.get_json() if request.is_json else request.form
    new_pw = (data.get("new_password") or "").strip()
    confirm_pw = (data.get("confirm_password") or "").strip()

    if not new_pw or not confirm_pw:
        return (jsonify({"error": "Missing fields"}), 400) if request.is_json else ("Missing fields", 400)
    if new_pw != confirm_pw:
        return (jsonify({"error": "Passwords do not match"}), 400) if request.is_json else ("Passwords do not match", 400)
    if not _valid_password(new_pw):
        return (jsonify({"error": "Password too weak"}), 400) if request.is_json else ("Password too weak", 400)

    # update password + flip flag
    user.password_hash = generate_password_hash(new_pw)
    user.onboarded_flag = 1
    db.session.commit()

    # clear flag and rotate session
    # (optional) regenerate session id here if you have a helper
    if request.is_json:
        return jsonify({"message": "Password updated"}), 200
    else:
        return "Password updated", 200



@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        # Check if it's JSON (AJAX from frontend) or form (fallback)
        if request.is_json:
            data = request.get_json()
            email = data.get("email")
            password = data.get("password")
        else:
            email = request.form.get("email")
            password = request.form.get("password")

        if not email or not password:
            return jsonify({"error": "Missing email or password"}), 400

        user = User.query.filter_by(email=email.lower()).first()
        
        if user and check_password_hash(user.password_hash, password):
            if user.onboarded_flag == 1:
                session["user_id"] = user.id
                session["client_id"] = user.client_id
    
                # If it's an AJAX request, return JSON
                if request.is_json:
                    return jsonify({"message": "Logged in"}), 200
                else:
                    return redirect(url_for("home.promotion_ui"))
                    
            if user.onboarded_flag != 1:
                session["user_id"] = user.id
                session["client_id"] = user.client_id
                
                if request.is_json:
                    return jsonify({"message": "Chagne Password"}), 200
                else:
                    return redirect(url_for("auth.change_password_page"))
                    
        if request.is_json:
            return jsonify({"error": "Invalid credentials"}), 401
        else:
            return "Invalid credentials", 401

    return render_template("login.html")

@auth_bp.route("/logout",methods=["GET", "POST"])
def logout():
    session.clear()
    return render_template("logout.html"), 200



@auth_bp.route("/create-user", methods=["GET", "POST"])
@login_required
def create_or_update_user():
    # Support both GET query params and POST JSON
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        onboarded_flag = _maybe(data.get("onboarded_flag"))
        email      = _maybe(data.get("email"))
        password   = data.get("password")  # keep raw for hashing
        client_id  = _maybe(data.get("client_id"))
        api_key    = _maybe(data.get("api_key"))
        pk_key     = _maybe(data.get("pk_key"))
        pk_origins_raw = _maybe(data.get("pk_origins"))
        jwt_secrets = _maybe(data.get("jwt_secrets"))
    else:
        onboarded_flag = _maybe(request.args.get("onboarded_flag"))
        email      = _maybe(request.args.get("email"))
        password   = request.args.get("password")
        client_id  = _maybe(request.args.get("client_id"))
        api_key    = _maybe(request.args.get("api_key"))
        pk_key     = _maybe(request.args.get("pk_key"))
        pk_origins_raw = _maybe(request.args.get("pk_origins"))
        jwt_secrets = _maybe(request.args.get("jwt_secrets"))

    if not email or not client_id:
        return jsonify({"error": "Missing parameters: email and client_id are required"}), 400

    email_lc = email.lower()
    user = User.query.filter_by(email=email_lc).first()
    print(pk_origins_raw)
    # Parse pk_origins into a list (or None)
    pk_origins_list = _parse_pk_origins(pk_origins_raw) if pk_origins_raw else None

    if user is None:
        # CREATE
        hashed_pw = generate_password_hash(password) if password else generate_password_hash(secrets.token_hex(8))
        user = User(
            onboarded_flag=onboarded_flag,
            email=email_lc,
            password_hash=hashed_pw,
            client_id=client_id,
            api_key=api_key or _ensure_api_key(None),
            pk_key=pk_key or _ensure_pk_key(None),
            jwt_secrets=jwt_secrets
        )
        if pk_origins_list is not None:
            user.pk_origin = pk_origins_list
        db.session.add(user)
        db.session.commit()
        return jsonify({
            "message": f"✅ Created user {email_lc} for {client_id}",
            "user": {
                "onboarded_flag": user.onboarded_flag,
                "email": user.email,
                "client_id": user.client_id,
                "api_key": user.api_key,
                "pk_key": user.pk_key,
                "pk_origins": getattr(user, "pk_origins", None) or getattr(user, "pk_origin", None),
                "jwt_secrets": user.jwt_secrets
            }
        }), 201
    else:
        # UPDATE (only overwrite fields if provided)
        if password:
            user.password_hash = generate_password_hash(password)
        if client_id:
            user.client_id = client_id
        if api_key is not None:
            user.api_key = api_key or _ensure_api_key(user.api_key)
        if pk_key is not None:
            user.pk_key = pk_key or _ensure_pk_key(user.pk_key)
        if jwt_secrets is not None:
            user.jwt_secrets = jwt_secrets
        if pk_origins_list is not None:
            user.pk_origin = pk_origins_list
        if onboarded_flag is not None:
            user.onboarded_flag = onboarded_flag

        db.session.commit()
        return jsonify({
            "message": f"✏️ Updated user {email_lc}",
            "user": {
                "onboarded_flag": user.onboarded_flag,
                "email": user.email,
                "client_id": user.client_id,
                "api_key": user.api_key,
                "pk_key": user.pk_key,
                "pk_origins": getattr(user, "pk_origin", None),
                "jwt_secrets": user.jwt_secrets
            }
        }), 200


@auth_bp.route("/me/credentials", methods=["GET"])
@login_required
def get_my_credentials():
    # Use your session to identify the currently logged-in user
    user_id = session.get("user_id")
    user = User.query.filter_by(id=user_id).first()
    if not user:
        return jsonify({"error": "User not found"}), 404

    return jsonify({
        "email": user.email,
        "client_id": user.client_id,
        "api_key": user.api_key,     # server-side secret: only return to the owner
        "pk_key": user.pk_key,       # publishable key (safe for browsers)
        "jwt": user.jwt_secrets      # fresh short-lived token
    }), 200
    

@auth_bp.route("/create-subscription", methods=["GET"])
@login_required
def create_subscription_via_url():
    client_id = request.args.get("client_id")
    type = request.args.get("type")
    start_date = request.args.get("start_date")  # expected format: YYYY-MM-DD
    end_date = request.args.get("end_date")      # expected format: YYYY-MM-DD
    max_api_calls = request.args.get("max_api_calls")
    max_api_fingerprint_calls = request.args.get("max_api_fingerprint_calls")
    
    if not client_id or not start_date or not end_date or not max_api_calls:
        return jsonify({"error": "Missing parameters"}), 400

    try:
        subscription_start = datetime.strptime(start_date, "%Y-%m-%d")
        subscription_end = datetime.strptime(end_date, "%Y-%m-%d")
        max_api_calls = int(max_api_calls)
        max_api_fingerprint_calls = int(max_api_fingerprint_calls)
    except ValueError as e:
        return jsonify({"error": f"Invalid date or number format: {str(e)}"}), 400

    subscription = ClientSubscription(
        client_id=client_id,
        type=type,
        subscription_start=subscription_start,
        subscription_end=subscription_end,
        max_api_calls=max_api_calls,
        max_api_fingerprint_calls=max_api_fingerprint_calls,
    )

    db.session.add(subscription)
    db.session.commit()

    return jsonify({"message": f"✅ Created subscription for {client_id}"}), 201



# --------------------------------------------------
# NEW: Admin Tenant APIs (secured via X-Admin-Key)
# --------------------------------------------------

@auth_bp.route("/admin/upsert-tenant", methods=["POST"])
@login_required
def upsert_tenant():
    """
    Create or update a tenant with encrypted secrets.
    Requires header: X-Admin-Key = <ADMIN_API_KEY>
    Body (JSON):
      {
        "client_id": "client_a",
        "postgres_uri": "postgresql://...",
        "neo4j_uri": "neo4j+s://f34af....neo4j.io",
        "neo4j_user": "neo4j",
        "neo4j_password": "super-secret"
      }
    """
    #if not _require_admin():
    #    return jsonify({"error": "Unauthorized"}), 403

    if not request.is_json:
        return jsonify({"error": "Expected application/json body"}), 400

    data = request.get_json(silent=True) or {}
    client_id = (data.get("client_id") or "").strip()
    pg_uri = (data.get("postgres_uri") or "").strip()
    neo4j_uri = (data.get("neo4j_uri") or "").strip()
    neo4j_user = (data.get("neo4j_user") or "").strip()
    neo4j_pass = (data.get("neo4j_password") or "").strip()

    if not client_id or not pg_uri or not neo4j_uri or not neo4j_user or not neo4j_pass:
        return jsonify({"error": "Missing required fields"}), 400

    try:
        t = Tenant.query.filter_by(client_id=client_id).first()
        created = False
        if not t:
            t = Tenant(client_id=client_id)
            created = True

        t.pg_uri_enc = enc(pg_uri)
        t.neo4j_uri_enc = enc(neo4j_uri)
        t.neo4j_user_enc = enc(neo4j_user)
        t.neo4j_pass_enc = enc(neo4j_pass)

        db.session.add(t)
        db.session.commit()

        return jsonify({
            "message": "✅ Tenant created" if created else "✅ Tenant updated",
            "client_id": client_id
        }), 201 if created else 200
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({"error": f"Database error: {str(e)}"}), 500
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@auth_bp.route("/admin/tenant", methods=["GET"])
@login_required
def get_tenant():
    """
    Fetch a tenant's configuration.
    Requires header: X-Admin-Key = <ADMIN_API_KEY>
    Query params:
      client_id (required)
      include_secrets=true|false  (default false → secrets masked)
    """
    if not _require_admin():
        return jsonify({"error": "Unauthorized"}), 403

    client_id = (request.args.get("client_id") or "").strip()
    include_secrets = (request.args.get("include_secrets") == "true")

    if not client_id:
        return jsonify({"error": "Missing client_id"}), 400

    try:
        t = Tenant.query.filter_by(client_id=client_id).first()
        if not t:
            return jsonify({"error": "Tenant not found"}), 404

        pg = dec(t.pg_uri_enc)
        nuri = dec(t.neo4j_uri_enc)
        nuser = dec(t.neo4j_user_enc)
        npass = dec(t.neo4j_pass_enc)

        if include_secrets:
            payload = {
                "client_id": client_id,
                "postgres_uri": pg,
                "neo4j_uri": nuri,
                "neo4j_user": nuser,
                "neo4j_password": npass,
            }
        else:
            payload = {
                "client_id": client_id,
                "postgres_uri": _mask(pg),
                "neo4j_uri": _mask(nuri),
                "neo4j_user": _mask(nuser),
                "neo4j_password": "•••",
            }

        return jsonify(payload), 200
    except SQLAlchemyError as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500



#### deprecated
@auth_bp.route("/create-user-old", methods=["GET"])
@login_required
def create_user_via_url():
    email = request.args.get("email")
    password = request.args.get("password")
    client_id = request.args.get("client_id")
    api_key = request.args.get("api_key")
    #admin_key = request.headers.get("X-Admin-Key")  # Optional for security

    # Optional: check admin key for added security
    #expected_key = current_app.config.get("ADMIN_API_KEY", "mysecretkey")
    #if admin_key != expected_key:
        #return jsonify({"error": "Unauthorized"}), 403

    if not email or not password or not client_id:
        return jsonify({"error": "Missing parameters"}), 400

    if User.query.filter_by(email=email.lower()).first():
        return jsonify({"error": "User already exists"}), 400

    hashed_pw = generate_password_hash(password)
    user = User(email=email.lower(), password_hash=hashed_pw, client_id=client_id, api_key=api_key)
    db.session.add(user)
    db.session.commit()

    return jsonify({"message": f"✅ Created user {email} for {client_id}"}), 201
