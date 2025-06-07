from flask import Blueprint, request, jsonify, current_app

promocode_bp = Blueprint("promocode", __name__, url_prefix="/api/promocode")

@promocode_bp.route("/usage", methods=["GET"])
def usage():
    promocode = request.args.get("promocode", "").strip()

    # Modified Cypher Query to check abusive usage of the promocode
    query = """
    // Step 1: Find all orders using the promocode with their order date
    MATCH (c:Customer)-[:PLACED]->(o:Order)-[:HAS_ATTRIBUTE]->(a:Attribute {type: 'promocode', value: $promocode})
    WITH c, o, date(datetime(o.created_at)) AS order_date
    
    // Step 2: Collect shared attributes for the customer
    MATCH (c)-[:PLACED]->(:Order)-[:HAS_ATTRIBUTE]->(attr)
    WHERE attr.type IN ['email', 'phone', 'device_id', 'card_details']
    WITH o, order_date, COLLECT(DISTINCT attr.value) AS shared_attrs
    
    // Step 3: Use a subquery to find how many different customers used the same promocode via shared attributes
    CALL {
        WITH shared_attrs, order_date
        MATCH (c2:Customer)-[:PLACED]->(o2:Order)-[:HAS_ATTRIBUTE]->(attr2)
        WHERE attr2.value IN shared_attrs AND attr2.type IN ['email', 'phone', 'device_id', 'card_details']
        MATCH (o2)-[:HAS_ATTRIBUTE]->(a2:Attribute {type: 'promocode', value: $promocode})
        RETURN DISTINCT o2.id AS order_id, COUNT(DISTINCT c2) AS user_count
    }
    WITH order_date, order_id, user_count
    
    // Step 4: Aggregate abuse per day
    WITH order_date,
         COUNT(DISTINCT order_id) AS total_orders,
         COUNT(DISTINCT CASE WHEN user_count > 1 THEN order_id END) AS abusive_orders
    
    RETURN 
      order_date,
      total_orders,
      abusive_orders,
      (abusive_orders * 100.0 / total_orders) AS abuse_rate
    ORDER BY order_date
"""
    

    params = {"promocode": promocode} if promocode else {}

    try:
        with current_app.neo4j_driver.session() as session: 
            result = session.run(query, params)
            records = [record.data() for record in result]

            if records:
                return jsonify(records), 200
            else:
                return jsonify({"message": "No data found for this promocode"}), 200

    except Exception as e:
        return jsonify({"error": "Database error", "details": str(e)}), 500

@promocode_bp.route("/order-count", methods=["GET"])
def order_count():
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

    // Step 3: Group by promocode and count the number of orders for each promocode
    MATCH (order2)-[:HAS_ATTRIBUTE]->(promocode_attr:Attribute {type: 'promocode'})
    WITH promocode_attr.value AS promocode, COUNT(DISTINCT order2.id) AS total_orders
    ORDER BY total_orders DESC

    // Step 4: Return the list of promocodes and their associated total order counts
    RETURN 
        COLLECT({promocode: promocode, total_orders: total_orders}) AS promocode_stats
    """

    params = {"email": email}

    try:
        with current_app.neo4j_driver.session() as session:
            result = session.run(query, params)
            record = result.single()

            if record:
                return jsonify({
                    "promocode_stats": record["promocode_stats"]
                }), 200
            else:
                return jsonify({"message": "No data found for this email"}), 200

    except Exception as e:
        return jsonify({"error": "Database error", "details": str(e)}), 500


@promocode_bp.route("/abuse-by-day", methods=["GET"])
def abuse_by_day():
    promocode = request.args.get("promocode", "").strip()

    if not promocode:
        return jsonify({"error": "Missing promocode parameter"}), 400

    query = """
    MATCH (c:Customer)-[:PLACED]->(o:Order)-[:HAS_ATTRIBUTE]->(a:Attribute {type: 'promocode', value: $promocode})
    WITH o, date(o.created_at) AS order_date
    MATCH (o)-[:HAS_ATTRIBUTE]->(attr)
    WHERE attr.type IN ['phone', 'device_id', 'card_details', 'email']
    WITH o, order_date, COLLECT(DISTINCT attr.value) AS shared_attrs

    MATCH (c2:Customer)-[:PLACED]->(o2:Order)-[:HAS_ATTRIBUTE]->(attr2)
    WHERE attr2.value IN shared_attrs AND attr2.type IN ['phone', 'device_id', 'card_details', 'email']
    MATCH (o2)-[:HAS_ATTRIBUTE]->(a2:Attribute {type: 'promocode', value: $promocode})

    WITH order_date, COUNT(DISTINCT o2) AS total_orders,
         COUNT(DISTINCT CASE WHEN COUNT(o2) > 1 THEN o2 END) AS abusive_orders
    RETURN order_date, total_orders, abusive_orders,
           (abusive_orders * 100.0 / total_orders) AS abuse_rate
    ORDER BY order_date
    """

    params = {"promocode": promocode}

    try:
        with current_app.neo4j_driver.session() as session:
            result = session.run(query, params)
            data = [record.data() for record in result]
            return jsonify(data), 200
    except Exception as e:
        return jsonify({"error": "Database error", "details": str(e)}), 500
