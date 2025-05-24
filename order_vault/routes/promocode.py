from flask import Blueprint, request, jsonify, current_app

promocode_bp = Blueprint("promocode", __name__, url_prefix="/api/promocode")

@promocode_bp.route("/usage", methods=["GET"])
def usage():
    """
    Returns usage and abuse statistics for a given promocode.
    Query params:
      - promocode: the promotional code to analyze (required)
    """
    promo = request.args.get("promocode", "").strip()
    if not promo:
        return jsonify({"error": "Missing promocode parameter"}), 400

    cypher = """
    // Step 1: Find all customers who used the promocode
    MATCH (c:Customer)-[:PLACED]->(order:Order)-[:HAS_ATTRIBUTE]->(promocode_attr:Attribute {type: 'promocode', value: $promocode})
    WITH c, order

    // Step 2: Collect shared attributes for those customers
    MATCH (c)-[:PLACED]->(order)-[:HAS_ATTRIBUTE]->(attr)
    WHERE attr.type IN ['phone', 'device_id', 'card_details', 'email']
    WITH c, COLLECT(DISTINCT attr.value) AS shared_attributes, order

    // Step 3: Find linked customers by shared attributes
    MATCH (c2:Customer)-[:PLACED]->(order2:Order)-[:HAS_ATTRIBUTE]->(attr2)
    WHERE attr2.value IN shared_attributes AND attr2.type IN ['phone', 'device_id', 'card_details', 'email']

    // Step 4: Count connected orders using the same promocode
    MATCH (c2)-[:PLACED]->(order2)-[:HAS_ATTRIBUTE]->(promocode_attr2:Attribute {type: 'promocode', value: $promocode})
    WITH c, COUNT(DISTINCT order.id) AS total_orders, COUNT(DISTINCT order2.id) AS connected_orders

    // Step 5: Flag abusive if connected_orders > 1
    WITH COUNT(DISTINCT c.email) AS total_usage, SUM(CASE WHEN connected_orders > 1 THEN connected_orders ELSE 0 END) AS abusive_usage_count

    // Step 6: Calculate abuse rate
    RETURN total_usage, abusive_usage_count, (abusive_usage_count * 100.0 / total_usage) AS abuse_rate_percentage
    """

    params = {"promocode": promo}
    try:
        with current_app.neo4j_driver.session() as session:
            result = session.run(cypher, params)
            records = [rec.data() for rec in result]
            if records:
                return jsonify(records), 200
            else:
                return jsonify({"message": "No data found for this promocode"}), 200
    except Exception as e:
        return jsonify({"error": "Database error", "details": str(e)}), 500

@promocode_bp.route("/order-count", methods=["GET"])
def order_count():
    """
    Returns the number of orders per promocode for customers connected by shared attributes.
    Query params:
      - email: customer email to base the network on (required)
    """
    email = request.args.get("email", "").strip().lower()
    if not email:
        return jsonify({"error": "Missing email parameter"}), 400

    cypher = """
    // Step 1: Collect shared attributes for the given customer
    MATCH (c:Customer {email: $email})-[:PLACED]->(order:Order)-[:HAS_ATTRIBUTE]->(attr)
    WHERE attr.type IN ['phone', 'device_id', 'card_details', 'email']
    WITH COLLECT(DISTINCT attr.value) AS shared_attributes

    // Step 2: Find all related orders by those attributes
    MATCH (c2:Customer)-[:PLACED]->(order2:Order)-[:HAS_ATTRIBUTE]->(attr2)
    WHERE attr2.value IN shared_attributes AND attr2.type IN ['phone', 'device_id', 'card_details', 'email']

    // Step 3: Group by promocode and count orders
    MATCH (order2)-[:HAS_ATTRIBUTE]->(p:Attribute {type: 'promocode'})
    RETURN p.value AS promocode, COUNT(DISTINCT order2.id) AS total_orders
    ORDER BY total_orders DESC
    """

    params = {"email": email}
    try:
        with current_app.neo4j_driver.session() as session:
            records = session.run(cypher, params)
            stats = [{"promocode": rec["promocode"], "total_orders": rec["total_orders"]} for rec in records]
            return jsonify({"promocode_stats": stats}), 200
    except Exception as e:
        return jsonify({"error": "Database error", "details": str(e)}), 500
