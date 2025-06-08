from flask import Blueprint, request, jsonify, current_app, g
import traceback
from auth.session import load_tenant

promocode_bp = Blueprint("promocode", __name__, url_prefix="/api/promocode")

@promocode_bp.route("/usage", methods=["GET"])
def usage():
    load_tenant()
    promocode = request.args.get("promocode", "").strip()

    # Modified Cypher Query to check abusive usage of the promocode
    query = """
    // Step 1: Find all orders with the promocode and their customers
    MATCH (c:Customer)-[:PLACED]->(o:Order)-[:HAS_ATTRIBUTE]->(promo:Attribute {type: 'promocode', value: $promocode})
    WITH DISTINCT c, o
    
    // Step 2: Find identity values for each customer
    MATCH (c)-[:PLACED]->(:Order)-[:HAS_ATTRIBUTE]->(idAttr)
    WHERE idAttr.type IN ['email', 'phone', 'device_id', 'card_details']
    WITH c, o, COLLECT(DISTINCT idAttr.value) AS identity_keys
    
    // Step 3: Map customers to identity keys
    UNWIND identity_keys AS identity
    WITH identity, c
    
    // Step 4: Build network groups using shared identity keys
    WITH identity, COLLECT(DISTINCT c) AS customers
    UNWIND customers AS customer_in_group
    WITH identity, customer_in_group
    WITH customer_in_group, COLLECT(DISTINCT identity) AS all_identities
    
    // Step 5: Collect all customers in the same network
    UNWIND all_identities AS shared_id
    MATCH (c2:Customer)-[:PLACED]->(o2:Order)-[:HAS_ATTRIBUTE]->(attr2)
    WHERE attr2.value = shared_id AND attr2.type IN ['email', 'phone', 'device_id', 'card_details']
    MATCH (o2)-[:HAS_ATTRIBUTE]->(a2:Attribute {type: 'promocode', value: $promocode})
    
    // Step 6: Group by identity network
    WITH COLLECT(DISTINCT o2) AS network_orders, COLLECT(DISTINCT c2.email) AS network_emails
    
    // Step 7: For each group, mark one as genuine, rest as abusive
    WITH 
      SIZE(network_orders) AS order_count,
      SIZE(network_emails) AS user_count,
      CASE WHEN SIZE(network_orders) > 1 THEN SIZE(network_orders) - 1 ELSE 0 END AS abusive_orders,
      CASE WHEN SIZE(network_orders) > 1 THEN SIZE(network_emails) - 1 ELSE 0 END AS abusive_users,
      1 AS genuine_order,
      1 AS genuine_user
    
    // Step 8: Aggregate unique totals across all identity groups
    RETURN
      SUM(genuine_order) AS genuine_orders,
      SUM(abusive_orders) AS abusive_orders,
      SUM(genuine_user) AS genuine_users,
      SUM(abusive_users) AS abusive_users,
      SUM(genuine_order + abusive_orders) AS total_orders,
      SUM(genuine_user + abusive_users) AS total_users,
      ROUND(100.0 * SUM(abusive_orders) / SUM(genuine_order + abusive_orders), 2) AS abuse_order_rate_percentage,
      ROUND(100.0 * SUM(abusive_users) / SUM(genuine_user + abusive_users), 2) AS abuse_user_rate_percentage
      """
    

    params = {"promocode": promocode} if promocode else {}

    try:
        with g.neo4j_driver.session() as session: 
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
    load_tenant()
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
        with g.neo4j_driver.session() as session:
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
    load_tenant()
    promocode = request.args.get("promocode", "").strip()

    if not promocode:
        return jsonify({"error": "Missing promocode parameter"}), 400

    query = """
    // Step 1: Get all orders that used the promocode, and their identity
    MATCH (c:Customer)-[:PLACED]->(o:Order)-[:HAS_ATTRIBUTE]->(a:Attribute {type: 'promocode', value: $promocode})
    WITH c, o, date(datetime(o.created_at)) AS order_date
    
    // Step 2: Collect identity attributes for each customer
    MATCH (c)-[:PLACED]->(:Order)-[:HAS_ATTRIBUTE]->(attr)
    WHERE attr.type IN ['email', 'phone', 'device_id', 'card_details']
    WITH c, o, order_date, COLLECT(DISTINCT attr.value) AS identity_attrs
    
    // Step 3: Count how many orders from that identity network used the promocode
    CALL {
      WITH identity_attrs
      MATCH (c2:Customer)-[:PLACED]->(o2:Order)-[:HAS_ATTRIBUTE]->(attr2)
      WHERE attr2.value IN identity_attrs AND attr2.type IN ['email', 'phone', 'device_id', 'card_details']
      MATCH (o2)-[:HAS_ATTRIBUTE]->(a2:Attribute {type: 'promocode', value: $promocode})
      RETURN COUNT(DISTINCT o2) AS promo_orders_in_network
    }
    
    // Step 4: Determine if this specific order is abusive (if network already used it)
    WITH o, order_date, 
         CASE WHEN promo_orders_in_network > 1 THEN 1 ELSE 0 END AS is_abusive
    
    // Step 5: Aggregate by day
    WITH order_date,
         COUNT(o) AS total_orders,
         SUM(is_abusive) AS abusive_orders
    WHERE order_date IS NOT NULL
    RETURN 
      order_date,
      total_orders,
      abusive_orders,
      ROUND(abusive_orders * 100.0 / total_orders, 2) AS abuse_rate
    ORDER BY order_date
    """

    params = {"promocode": promocode}


    try:
        with g.neo4j_driver.session() as session: 
            result = session.run(query, params)
            records = []
            
            for record in result:
                row = record.data()
                if "order_date" in row and hasattr(row["order_date"], "iso_format"):
                    row["order_date"] = row["order_date"].iso_format()  # Convert Neo4j Date to string
                records.append(row)
            
            return jsonify(records), 200

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": "Database error", "details": str(e)}), 500

