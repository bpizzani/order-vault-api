from flask import Blueprint, request, jsonify, session
from order_vault.models.user import User
from werkzeug.security import check_password_hash

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.json
    user = User.query.filter_by(email=data["email"]).first()
    if not user or not check_password_hash(user.password_hash, data["password"]):
        return jsonify({"error": "Invalid credentials"}), 401

    session["user_id"] = user.id
    session["client_id"] = user.client_id
    return jsonify({"message": "Logged in", "client_id": user.client_id})


@auth_bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"message": "Logged out"}), 200


@auth_bp.route("/create-user", methods=["GET"])
def create_user_via_url():
    email = request.args.get("email")
    password = request.args.get("password")
    client_id = request.args.get("client_id")
    admin_key = request.headers.get("X-Admin-Key")

    if admin_key != current_app.config.get("ADMIN_API_KEY"):
        return jsonify({"error": "Unauthorized"}), 403

    if not email or not password or not client_id:
        return jsonify({"error": "Missing parameters"}), 400

    if User.query.filter_by(email=email.lower()).first():
        return jsonify({"error": "User already exists"}), 400

    hashed_pw = generate_password_hash(password)
    user = User(email=email.lower(), password_hash=hashed_pw, client_id=client_id)
    db.session.add(user)
    db.session.commit()

    return jsonify({"message": f"✅ Created user {email} for {client_id}"}), 201



#deprecated
@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.json

    required_fields = ["email", "password", "client_id"]
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Missing fields"}), 400

    email = data["email"].strip().lower()
    password = data["password"]
    client_id = data["client_id"].strip()

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "User already exists"}), 400

    try:
        hashed_pw = generate_password_hash(password)
        user = User(email=email, password_hash=hashed_pw, client_id=client_id)
        db.session.add(user)
        db.session.commit()
        return jsonify({"message": f"User {email} created for client {client_id}"}), 201
    except Exception as e:
        return jsonify({"error": "Could not create user", "details": str(e)}), 500


