from flask import Blueprint, request, jsonify, current_app

customer_bp = Blueprint("customer", __name__, url_prefix="/api/customer")

@customer_bp.route("/attributes-summary", methods=["GET"])
def summary():
    """
    Returns total orders, distinct cards, phones, devices for a given customer email.
    Query params:
      - email: customer's email address (required)
    """
    email = request.args.get("email", "").strip().lower()
    if not email:
        return jsonify({"error": "Missing email parameter"}), 400

    cypher = """
    MATCH (c:Customer {email: $email})-[:PLACED]->(order:Order)-[:HAS_ATTRIBUTE]->(attr)
    WHERE attr.type IN ['phone','device_id','email','card_details']
    RETURN
      COUNT(DISTINCT order) AS total_orders,
      COUNT(DISTINCT CASE WHEN attr.type = 'card_details' THEN attr.value END) AS distinct_cards,
      COUNT(DISTINCT CASE WHEN attr.type = 'phone' THEN attr.value END) AS distinct_phones,
      COUNT(DISTINCT CASE WHEN attr.type = 'device_id' THEN attr.value END) AS distinct_devices
    """
    params = {"email": email}

    try:
        with current_app.neo4j_driver.session() as session:
            record = session.run(cypher, params).single()
            if record:
                return jsonify({
                    "total_orders": record["total_orders"],
                    "distinct_cards": record["distinct_cards"],
                    "distinct_phones": record["distinct_phones"],
                    "distinct_devices": record["distinct_devices"]
                }), 200
            else:
                return jsonify({"message": "No data found for this email"}), 200
    except Exception as e:
        return jsonify({"error": "Database error", "details": str(e)}), 500

@customer_bp.route("/attributes-network", methods=["GET"])
def network():
    """
    Returns network summary of connected customers and orders based on shared attributes.
    Query params:
      - email: customer's email address (required)
    """
    email = request.args.get("email", "").strip().lower()
    if not email:
        return jsonify({"error": "Missing email parameter"}), 400

    cypher = """
    // Step 1: Collect shared attributes for the customer
    MATCH (c:Customer {email: $email})-[:PLACED]->(order:Order)-[:HAS_ATTRIBUTE]->(attr)
    WHERE attr.type IN ['phone','device_id','card_details','email']
    WITH COLLECT(DISTINCT attr.value) AS shared_attributes
    
    // Step 2: Find other customers linked by those attributes
    MATCH (c2:Customer)-[:PLACED]->(order2:Order)-[:HAS_ATTRIBUTE]->(attr2)
    WHERE attr2.value IN shared_attributes AND attr2.type IN ['phone','device_id','card_details','email']
    
    RETURN
      COUNT(DISTINCT c2.email) AS connected_customers,
      COUNT(DISTINCT order2.id) AS connected_orders,
      COUNT(DISTINCT CASE WHEN attr2.type='card_details' THEN attr2.value END) AS distinct_cards,
      COUNT(DISTINCT CASE WHEN attr2.type='phone' THEN attr2.value END) AS distinct_phones,
      COUNT(DISTINCT CASE WHEN attr2.type='device_id' THEN attr2.value END) AS distinct_devices,
      COUNT(DISTINCT CASE WHEN attr2.type='promocode' THEN attr2.value END) AS distinct_promocodes,
      COUNT(CASE WHEN attr2.type='promocode' THEN attr2.value END) AS total_promocodes
    """
    params = {"email": email}

    try:
        with current_app.neo4j_driver.session() as session:
            record = session.run(cypher, params).single()
            if record:
                return jsonify({
                    "connected_customers": record["connected_customers"],
                    "connected_orders": record["connected_orders"],
                    "distinct_cards": record["distinct_cards"],
                    "distinct_phones": record["distinct_phones"],
                    "distinct_devices": record["distinct_devices"],
                    "distinct_promocodes": record["distinct_promocodes"],
                    "total_promocodes": record["total_promocodes"]
                }), 200
            else:
                return jsonify({"message": "No data found for this email"}), 200
    except Exception as e:
        return jsonify({"error": "Database error", "details": str(e)}), 500
