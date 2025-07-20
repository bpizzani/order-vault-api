from flask import Blueprint, request, jsonify, session, current_app, redirect, url_for, render_template
from order_vault.models.user import User
from order_vault.main import db
from werkzeug.security import check_password_hash, generate_password_hash

auth_bp = Blueprint("auth", __name__)

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


@auth_bp.route("/delete-db", methods=["GET","POST"])
def delete_db_version():
    try:
        db.session.execute("DELETE FROM alembic_version;")
        db.session.commit()
        return render_template("logout.html"), 200
    except Exception as e:
        current_app.logger.error(f"Failed to delete alembic_version: {e}")
        return f"Error: {str(e)}", 500


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


