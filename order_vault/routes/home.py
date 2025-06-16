from flask import Blueprint, render_template
from flask import request, session, jsonify
from werkzeug.security import check_password_hash
from order_vault.utils.auth import login_required

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

