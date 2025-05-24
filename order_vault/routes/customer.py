from flask import Blueprint, request, jsonify, current_app

customer_bp = Blueprint("customer", __name__, url_prefix="/api/customer")

@customer_bp.route("/attributes-summary")
def summary():
    email = request.args.get("email",""
        ).strip().lower()
    if not email:
        return jsonify({"error":"Missing email"}), 400
    q = """
    MATCH (c:Customer {email:$email})-[:PLACED]->(o:Order)-[:HAS_ATTRIBUTE]->(attr)
    RETURN ...
    """
    rec = current_app.neo4j_driver.session().run(q, {"email":email}).single()
    return jsonify(rec.data()), 200
