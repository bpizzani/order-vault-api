from flask import Blueprint, request, jsonify, current_app

customer_bp = Blueprint("customer", __name__, url_prefix="/api/customer")

@customer_bp.route("/attributes-summary", methods=["GET"])
def get_customer_attributes_summary():
    email = request.args.get("email", "").strip().lower()  # Normalize the email input

    if not email:
        return jsonify({"error": "Missing email parameter"}), 400

    print(f"Received email: {email}")  # Log the email received for debugging

    query = """
    MATCH (c:Customer {email: $email})-[:PLACED]->(order:Order)-[:HAS_ATTRIBUTE]->(attr)
    WHERE attr.type IN ['phone', 'device_id', 'email', 'card_details']
    RETURN 
        COUNT(DISTINCT order) AS total_orders,  // Total orders placed by the customer
        COUNT(DISTINCT CASE WHEN attr.type = 'card_details' THEN attr.value END) AS distinct_cards,
        COUNT(DISTINCT CASE WHEN attr.type = 'phone' THEN attr.value END) AS distinct_phones,
        COUNT(DISTINCT CASE WHEN attr.type = 'device_id' THEN attr.value END) AS distinct_devices
    """

    params = {"email": email}

    try:
        with current_app.neo4j_driver.session() as session:
            result = session.run(query, params)
            record = result.single()

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
def get_network_attributes():
    email = request.args.get("email", "").strip().lower()

    if not email:
        return jsonify({"error": "Missing email parameter"}), 400

    query = """
    // Step 1: Find the customer's shared attributes (phone, device_id, card_details, promocode)
    MATCH (c:Customer {email: $email})-[:PLACED]->(order:Order)-[:HAS_ATTRIBUTE]->(attr)
    WHERE attr.type IN ['phone', 'device_id', 'card_details','email']
    WITH COLLECT(DISTINCT attr.value) AS shared_attributes  // Collect shared attributes

    // Step 2: Find all customers connected by shared attributes (same phone, device_id, card_details, promocode)
    MATCH (c2:Customer)-[:PLACED]->(order2:Order)-[:HAS_ATTRIBUTE]->(attr2)
    WHERE attr2.value IN shared_attributes AND attr2.type IN ['phone', 'device_id', 'card_details','email']

    // Counting connected customers and their distinct attributes (card_details, phone, device_id, promocode)
    RETURN 
        COUNT(DISTINCT c2.email) AS connected_customers,  // Count distinct connected customers
        COUNT(DISTINCT order2.id) AS connected_orders,  // Count distinct connected orders
        COUNT(DISTINCT CASE WHEN attr2.type = 'card_details' THEN attr2.value END) AS distinct_cards,  // Count distinct card_details
        COUNT(DISTINCT CASE WHEN attr2.type = 'phone' THEN attr2.value END) AS distinct_phones,  // Count distinct phones
        COUNT(DISTINCT CASE WHEN attr2.type = 'device_id' THEN attr2.value END) AS distinct_devices,  // Count distinct device_id
        COUNT(DISTINCT CASE WHEN attr2.type = 'promocode' THEN attr2.value END) AS distinct_promocodes,  // Count distinct promocodes
        COUNT(CASE WHEN attr2.type = 'promocode' THEN attr2.value END) AS total_promocodes  // Count total promocodes
    """

    params = {"email": email}

    try:
        with current_app.neo4j_driver.session() as session:
            result = session.run(query, params)
            record = result.single()

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
