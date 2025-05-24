from flask import Blueprint, request, jsonify, current_app

bp = Blueprint("customer", __name__, url_prefix="/api/customer")

@bp.route("/attributes-summary", methods=["GET"])
def summary():
    email = request.args.get("email", "").lower()
    if not email:
        return jsonify({"error": "Missing email"}), 400

    q = """
    MATCH (c:Customer {email:$email})-[:PLACED]->(o:Order)-[:HAS_ATTRIBUTE]->(attr)
    WHERE attr.type IN ['phone','device_id','email','card_details']
    RETURN
      COUNT(DISTINCT o) AS total_orders,
      COUNT(DISTINCT CASE WHEN attr.type='card_details' THEN attr.value END) AS distinct_cards,
      COUNT(DISTINCT CASE WHEN attr.type='phone' THEN attr.value END) AS distinct_phones,
      COUNT(DISTINCT CASE WHEN attr.type='device_id' THEN attr.value END) AS distinct_devices
    """
    rec = current_app.neo4j_driver.session().run(q, {"email": email}).single()
    return jsonify(rec.data()), 200

@bp.route("/attributes-network", methods=["GET"])
def network():
    email = request.args.get("email", "").lower()
    if not email:
        return jsonify({"error": "Missing email"}), 400

    q = """…"""  # your long cypher from before
    rec = current_app.neo4j_driver.session().run(q, {"email": email}).single()
    return jsonify(rec.data()), 200

@bp.route("/promocode-order-count", methods=["GET"])
def promocode_count():
    email = request.args.get("email", "").lower()
    if not email:
        return jsonify({"error": "Missing email"}), 400

    q = """…"""  # your cypher for promocode stats
    rec = current_app.neo4j_driver.session().run(q, {"email": email}).single()
    return jsonify({"promocode_stats": rec["promocode_stats"]}), 200
