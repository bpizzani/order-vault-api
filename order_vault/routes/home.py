from flask import Blueprint, render_template, send_from_directory, request, session, jsonify
from werkzeug.security import check_password_hash
from order_vault.utils.auth import login_required, require_subscription_in
from order_vault.main import db
from sqlalchemy import text
from order_vault.auth.api_auth import require_api_key_fingerprint
from order_vault.models.client_subscription import ClientSubscription
from datetime import datetime

home_bp = Blueprint("home", __name__, url_prefix="/")

@home_bp.route("/main", methods=["GET"])
@login_required
@require_subscription_in("demo","admin",None)
def home():
    return render_template("home2.html")

@home_bp.route("/admin", methods=["GET"])
@login_required
@require_subscription_in("admin",None)
def admin_ui():
    return render_template("admin.html")

@home_bp.route("/promotion_dashboard", methods=["GET"])
@login_required
@require_subscription_in("demo","admin",None)
def promotion_ui():
    return render_template("promotion_dashboard.html")
    
@home_bp.route('/rules')
@login_required
@require_subscription_in("demo","admin",None)
def rules_ui():
    return render_template('rules.html')

@home_bp.route("/island", methods=["GET"])
@login_required
@require_subscription_in("demo","admin",None)
def customer_ui():
    return render_template("island.html")

@home_bp.route("/fingerprint", methods=["GET"])
@login_required
@require_subscription_in("demo","fingerprint_demo","admin",None)
def fingerprint_ui():
    return render_template("fingerprint.html")


@home_bp.route("/update-subscription-limit-deprecated", methods=["GET", "POST"])
def update_subscription_limit_deprecated():
    client_id = request.args.get("client_id")
    type = request.args.get("type")
    new_limit = request.args.get("max_api_calls")
    new_limit_fingerprint = request.args.get("max_api_fingerprint_calls")
    
    if not client_id or not new_limit:
        return jsonify({"error": "Missing client_id or max_api_calls"}), 400

    try:
        new_limit = int(new_limit)
        new_limit_fingerprint = int(new_limit_fingerprint)
    except ValueError:
        return jsonify({"error": "max_api_calls must be an integer"}), 400

    try:
        now = datetime.utcnow()

        # Fetch the active subscription
        subscription = ClientSubscription.query.filter(
            ClientSubscription.client_id == client_id,
            #ClientSubscription.type == type,
            ClientSubscription.subscription_start <= now,
            ClientSubscription.subscription_end >= now
        ).first()

        if not subscription:
            return jsonify({"error": "No active subscription found for client"}), 404

        # Update the limit
        subscription.max_api_calls = new_limit
        subscription.max_api_fingerprint_calls  = new_limit_fingerprint
        subscription.type = type
        db.session.commit()

        return jsonify({"message": f"✅ Updated max_api_calls to {new_limit} for client '{client_id}'"}), 200

    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({"error": f"Database error: {str(e)}"}), 500

@home_bp.route("/update-subscription-limit", methods=["GET", "POST"])
def update_subscription_limit():
    client_id = request.args.get("client_id")
    type = request.args.get("type")
    new_limit = request.args.get("max_api_calls")
    new_limit_fingerprint = request.args.get("max_api_fingerprint_calls")
    new_start_date = request.args.get("start_date")  # YYYY-MM-DD
    new_end_date = request.args.get("end_date")      # YYYY-MM-DD

    if not client_id or not new_limit:
        return jsonify({"error": "Missing client_id or max_api_calls"}), 400

    try:
        new_limit = int(new_limit)
        new_limit_fingerprint = int(new_limit_fingerprint)
    except (ValueError, TypeError):
        return jsonify({"error": "max_api_calls and max_api_fingerprint_calls must be integers"}), 400

    try:
        now = datetime.utcnow()

        # Fetch the active subscription
        subscription = ClientSubscription.query.filter(
            ClientSubscription.client_id == client_id,
            ClientSubscription.subscription_start <= now,
            ClientSubscription.subscription_end >= now
        ).first()

        if not subscription:
            return jsonify({"error": "No active subscription found for client"}), 404

        # Update fields
        subscription.max_api_calls = new_limit
        subscription.max_api_fingerprint_calls = new_limit_fingerprint
        if type:
            subscription.type = type

        if new_start_date:
            try:
                subscription.subscription_start = datetime.strptime(new_start_date, "%Y-%m-%d")
            except ValueError:
                return jsonify({"error": "Invalid start_date format. Use YYYY-MM-DD"}), 400

        if new_end_date:
            try:
                subscription.subscription_end = datetime.strptime(new_end_date, "%Y-%m-%d")
            except ValueError:
                return jsonify({"error": "Invalid end_date format. Use YYYY-MM-DD"}), 400

        db.session.commit()

        return jsonify({
            "message": (
                f"✅ Updated subscription for client '{client_id}' "
                f"→ max_api_calls={new_limit}, max_api_fingerprint_calls={new_limit_fingerprint}, "
                f"start_date={subscription.subscription_start.date()}, end_date={subscription.subscription_end.date()}"
            )
        }), 200

    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({"error": f"Database error: {str(e)}"}), 500


@home_bp.route("/delete-db", methods=["GET","POST"])
def delete_db_version():
    try:
        db.session.execute(text("DELETE FROM alembic_version;"))
        db.session.commit()
        return render_template("logout.html"), 200
    except Exception as e:
        return f"Error: {str(e)}", 500

@home_bp.route("/delete-db-duplicates-api", methods=["GET","POST"])
def delete_db_api():
    try:
        db.session.execute(text("DELETE FROM users WHERE id NOT IN (  SELECT MAX(id)   FROM users  GROUP BY api_key );"))
        db.session.commit()
        return render_template("logout.html"), 200
    except Exception as e:
        return f"Error: {str(e)}", 500

@home_bp.route("/update-rule-client-null", methods=["GET","POST"])
def update_rule_db_client_id():
    try:
        db.session.execute(text("UPDATE rule SET client_id = 'admin92' WHERE client_id IS NULL;"))
        db.session.commit()
        return render_template("logout.html"), 200
    except Exception as e:
        return f"Error: {str(e)}", 500


@home_bp.route("/kill-db-connction", methods=["GET","POST"])
def kill_db_connection():
    try:
        db.session.execute(text("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE usename = 'u32cgla1pp9fm7'  AND state = 'idle'  AND pid <> pg_backend_pid();"))
        db.session.commit()
        return render_template("logout.html"), 200
    except Exception as e:
        return f"Error: {str(e)}", 500

@home_bp.route("/static/js/")
def no_listing():
    return "Access denied", 403

@home_bp.route("/sdk-loader")
@require_api_key_fingerprint
def serve_fingerprint_js():
    return send_from_directory("static/js", "fingerprint_es.js")

@home_bp.route("/sdk-loader")
@require_api_key_fingerprint
def serve_fingerprint_min_js():
    return send_from_directory("static/js", "fingerprint_es.min.js")


@home_bp.route("/documentation_web", methods=["GET"])
@login_required
def documentation_web():
    return render_template("fingerprint_web_documentation.html")


@home_bp.route("/documentation_android", methods=["GET"])
@login_required
def documentation_android():
    return render_template("fingerprint_android_documentation.html")


