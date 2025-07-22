from flask import Blueprint, render_template
from flask import request, session, jsonify
from werkzeug.security import check_password_hash
from order_vault.utils.auth import login_required
from order_vault.main import db
from sqlalchemy import text

home_bp = Blueprint("home", __name__, url_prefix="/")

@home_bp.route("/main", methods=["GET"])
@login_required
def home():
    return render_template("home2.html")

@home_bp.route("/test", methods=["GET"])
@login_required
def test():
    return render_template("test.html")

@home_bp.route("/promotion_dashboard", methods=["GET"])
@login_required
def promotion_ui():
    return render_template("promotion_dashboard.html")
    
@home_bp.route('/rules')
@login_required
def rules_ui():
    return render_template('rules.html')

@home_bp.route("/island", methods=["GET"])
@login_required
def customer_ui():
    return render_template("island.html")

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

@home_bp.route("/static/js/fingerprint_es.js")
def no_listing_v2():
    return "Access denied", 403

@home_bp.route("/static/js/fingerprint_es.min.js")
def no_listing_v2():
    return "Access denied", 403





