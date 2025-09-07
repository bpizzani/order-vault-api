from flask import Blueprint, request, jsonify, session, current_app, redirect, url_for, render_template
from order_vault.models.user import User
from order_vault.models.client_subscription import ClientSubscription
from order_vault.main import db
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime

# 🔽 NEW imports for the admin tenant API
from sqlalchemy.exc import SQLAlchemyError
from order_vault.models.tenant import Tenant
from order_vault.utils.crypto import enc, dec

auth_bp = Blueprint("auth", __name__)

# ----------------------------
# Helpers (admin key + masking)
# ----------------------------
def _require_admin() -> bool:
    expected = current_app.config.get("ADMIN_API_KEY")
    provided = request.headers.get("X-Admin-Key")
    # Optional convenience: allow ?admin_key=... in dev, but header takes precedence
    if not provided:
        provided = request.args.get("admin_key") or (request.json or {}).get("admin_key") if request.is_json else None
    return bool(expected) and provided == expected

def _mask(s: str, keep: int = 4) -> str:
    try:
        return (s or "")[:keep] + "•••" if s and len(s) > keep else "•••"
    except Exception:
        return "•••"


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
            session["user_id"] = user.id
            session["client_id"] = user.client_id

            # If it's an AJAX request, return JSON
            if request.is_json:
                return jsonify({"message": "Logged in"}), 200
            else:
                return redirect(url_for("home.promotion_ui"))

        if request.is_json:
            return jsonify({"error": "Invalid credentials"}), 401
        else:
            return "Invalid credentials", 401

    return render_template("login.html")

@auth_bp.route("/logout",methods=["GET", "POST"])
def logout():
    session.clear()
    return render_template("logout.html"), 200

@auth_bp.route("/create-user", methods=["GET"])
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


@auth_bp.route("/create-subscription", methods=["GET"])
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
    if not _require_admin():
        return jsonify({"error": "Unauthorized"}), 403

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
