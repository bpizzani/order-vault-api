from flask import Blueprint, render_template
from flask import request, session, jsonify
from werkzeug.security import check_password_hash
from order_vault.utils.auth import login_required
from order_vault.main import db

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
#@login_required
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
        db.session.execute("DELETE FROM alembic_version;")
        db.session.commit()
        return render_template("logout.html"), 200
    except Exception as e:
        current_app.logger.error(f"Failed to delete alembic_version: {e}")
        return f"Error: {str(e)}", 500
