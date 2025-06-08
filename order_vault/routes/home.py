from flask import Blueprint, render_template
from flask import request, session, jsonify
from werkzeug.security import check_password_hash
from order_vault.models.user import User

home_bp = Blueprint("home", __name__, url_prefix="/")

@home_bp.route("", methods=["GET"])
def home():
    return render_template("home2.html")

@home_bp.route("/promotion_dashboard", methods=["GET"])
def promotion_ui():
    return render_template("promotion_dashboard.html")
    
@home_bp.route('/rules')
def rules_ui():
    return render_template('rules.html')

@home_bp.route("/island", methods=["GET"])
def customer_ui():
    return render_template("island.html")

