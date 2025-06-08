from flask import Blueprint, render_template
from flask import request, session, jsonify
from werkzeug.security import check_password_hash
from order_vault.models import User

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

@app.route("/login", methods=["POST"])
def login():
    data = request.json
    user = User.query.filter_by(email=data["email"]).first()

    if not user or not check_password_hash(user.password_hash, data["password"]):
        return jsonify({"error": "Invalid credentials"}), 401

    # Save user ID and client_id in session
    session["user_id"] = user.id
    session["client_id"] = user.client_id

    return jsonify({"message": "Login successful", "client_id": user.client_id})


def get_logged_in_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    return User.query.get(user_id)
