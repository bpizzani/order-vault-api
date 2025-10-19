from flask import Blueprint, request, jsonify, current_app, g, session
from order_vault.utils.auth import login_required
import traceback
from datetime import datetime, timedelta

promocode_bp = Blueprint("promocode", __name__, url_prefix="/api/promocode")

def get_date_range_from_request(req):
    """
    Returns (start_iso, end_iso) where both are ISO strings that Neo4j `datetime()` can parse.
    Defaults to last 15 days until now.
    """
    end_s = req.args.get("end_date", "").strip()
    start_s = req.args.get("start_date", "").strip()

    # If client passes YYYY-MM-DD, expand to midnight and end-of-day
    def to_iso_ceil(dstr):
        # '2025-10-12' -> '2025-10-12T23:59:59Z'
        return f"{dstr}T23:59:59Z"

    def to_iso_floor(dstr):
        # '2025-10-01' -> '2025-10-01T00:00:00Z'
        return f"{dstr}T00:00:00Z"

    if start_s and end_s:
        start_iso = to_iso_floor(start_s)
        end_iso = to_iso_ceil(end_s)
    else:
        # default last 15 days window
        end = datetime.utcnow()
        start = end - timedelta(days=15)
        start_iso = start.strftime("%Y-%m-%dT%H:%M:%SZ")
        end_iso = end.strftime("%Y-%m-%dT%H:%M:%SZ")

    return start_iso, end_iso


@promocode_bp.route("/usage", methods=["GET"])
@login_required
def usage():
    promocode = request.args.get("promocode", "").strip()
    start_iso, end_iso = get_date_range_from_request(request)
    
    # Modified Cypher Query to check abusive usage of the promocode
    query = """// Step 1: Get all orders that used the promocode and their identity attributes
    MATCH (c:Customer)-[:PLACED]->(o:Order)
    WHERE o.promocode = $promocode
        AND datetime(o.created_at) >= datetime($start)
        AND datetime(o.created_at) <= datetime($end)
    WITH c, o, datetime(o.created_at) AS full_ts
    
    // Step 2: Get the identity attributes that define the customer's network
    MATCH (c)-[:PLACED]->(:Order)-[:HAS_ATTRIBUTE]->(attr)
    WHERE attr.type IN ['email', 'phone', 'device_id', 'card_details']
    WITH c, o, full_ts, COLLECT(DISTINCT attr.value) AS identity_attrs
    
    // Step 3: Find all orders in that network that used the same promocode
    CALL {
      WITH identity_attrs
      MATCH (c2:Customer)-[:PLACED]->(o2:Order)-[:HAS_ATTRIBUTE]->(attr2)
      WHERE attr2.value IN identity_attrs
        AND attr2.type IN ['email', 'phone', 'device_id', 'card_details']
        AND o2.promocode = $promocode
        AND datetime(o2.created_at) >= datetime($start)
        AND datetime(o2.created_at) <= datetime($end)
      RETURN COLLECT(DISTINCT datetime(o2.created_at)) AS sorted_usages
    }
    
    // Step 4: Determine if this order is abusive (not first in the network)
    WITH c, o, full_ts, apoc.coll.sort(sorted_usages) AS sorted_ts
    WITH 
      c.email AS user_email,
      full_ts,
      CASE WHEN full_ts > sorted_ts[0] THEN 1 ELSE 0 END AS is_abusive
    
    // Step 5: Aggregate counts
    WITH
      COUNT(*) AS total_orders,
      SUM(is_abusive) AS abusive_orders,
      COUNT(DISTINCT user_email) AS total_users,
      COUNT(DISTINCT CASE WHEN is_abusive = 1 THEN user_email END) AS abusive_users
    
    RETURN
      total_orders,
      abusive_orders,
      total_orders - abusive_orders AS genuine_orders,
      total_users,
      abusive_users,
      total_users - abusive_users AS genuine_users,
      ROUND(abusive_orders * 100.0 / total_orders, 2) AS abuse_order_rate_percentage,
      ROUND(abusive_users * 100.0 / total_users, 2) AS abuse_user_rate_percentage"""
    
    query_v1 = """// Step 1: Find all orders with the target promocode and their customers
    MATCH (c:Customer)-[:PLACED]->(o:Order)
    WHERE o.promocode = $promocode
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
    WITH customer_in_group, COLLECT(DISTINCT identity) AS all_identities
    
    // Step 5: Collect all customers in the same network
    UNWIND all_identities AS shared_id
    MATCH (c2:Customer)-[:PLACED]->(o2:Order)-[:HAS_ATTRIBUTE]->(attr2)
    WHERE attr2.value = shared_id AND attr2.type IN ['email', 'phone', 'device_id', 'card_details']
    AND o2.promocode = $promocode  // 👈 check promo on Order node
    
    // Step 6: Group by network and count
    WITH COLLECT(DISTINCT o2) AS network_orders, COLLECT(DISTINCT c2.email) AS network_emails
    
    // Step 7: Classify abuse
    WITH 
      SIZE(network_orders) AS order_count,
      SIZE(network_emails) AS user_count,
      CASE WHEN SIZE(network_orders) > 1 THEN SIZE(network_orders) - 1 ELSE 0 END AS abusive_orders,
      CASE WHEN SIZE(network_orders) > 1 THEN SIZE(network_emails) - 1 ELSE 0 END AS abusive_users,
      1 AS genuine_order,
      1 AS genuine_user
    
    // Step 8: Aggregate totals
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
    query_v0 = """
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

    params = {"promocode": promocode, "start": start_iso, "end": end_iso} if promocode else {}

    try:
        with g.neo4j_driver.session() as session_net: 
            result = session_net.run(query, params)
            records = [record.data() for record in result]

            if records:
                return jsonify(records), 200
            else:
                return jsonify({"message": "No data found for this promocode"}), 200

    except Exception as e:
        return jsonify({"error": "Database error", "details": str(e)}), 500

@promocode_bp.route("/order-count", methods=["GET"])
@login_required
def order_count():
    email = request.args.get("email", "").strip().lower()

    if not email:
        return jsonify({"error": "Missing email parameter"}), 400
        
    start_iso, end_iso = get_date_range_from_request(request)
    query = """
    // Step 1: Find the customer's shared attributes (phone, device_id, card_details, promocode)
    MATCH (c:Customer {email: $email})-[:PLACED]->(order:Order)-[:HAS_ATTRIBUTE]->(attr)
    WHERE attr.type IN ['phone', 'device_id', 'card_details','email']
      AND datetime(order.created_at) >= datetime($start)
      AND datetime(order.created_at) <= datetime($end)
    WITH COLLECT(DISTINCT attr.value) AS shared_attributes  // Collect shared attributes

    // Step 2: Find all customers connected by shared attributes (same phone, device_id, card_details, promocode)
    MATCH (c2:Customer)-[:PLACED]->(order2:Order)-[:HAS_ATTRIBUTE]->(attr2)
    WHERE attr2.value IN shared_attributes AND attr2.type IN ['phone', 'device_id', 'card_details','email']
          AND datetime(order2.created_at) >= datetime($start)
          AND datetime(order2.created_at) <= datetime($end)

    // Step 3: Group by promocode and count the number of orders for each promocode
    MATCH (order2)-[:HAS_ATTRIBUTE]->(promocode_attr:Attribute {type: 'promocode'})
    WITH promocode_attr.value AS promocode, COUNT(DISTINCT order2.id) AS total_orders
    ORDER BY total_orders DESC

    // Step 4: Return the list of promocodes and their associated total order counts
    RETURN 
        COLLECT({promocode: promocode, total_orders: total_orders}) AS promocode_stats
    """

    params = {"email": email, "start": start_iso, "end": end_iso}

    try:
        with g.neo4j_driver.session() as session_net:
            result = session_net.run(query, params)
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
@login_required
def abuse_by_day():
    promocode = request.args.get("promocode", "").strip()

    if not promocode:
        return jsonify({"error": "Missing promocode parameter"}), 400
    start_iso, end_iso = get_date_range_from_request(request)
    query = """
    // Step 1: Get all orders that used the promocode, and their identity
    MATCH (c:Customer)-[:PLACED]->(o:Order)
    WHERE o.promocode = $promocode
      AND datetime(o.created_at) >= datetime($start)
      AND datetime(o.created_at) <= datetime($end)
    WITH c, o, date(datetime(o.created_at)) AS order_date, datetime(o.created_at) AS full_ts
    
    // Step 2: Collect identity attributes for each customer
    MATCH (c)-[:PLACED]->(:Order)-[:HAS_ATTRIBUTE]->(attr)
    WHERE attr.type IN ['email', 'phone', 'device_id', 'card_details']
    WITH c, o, order_date, full_ts, COLLECT(DISTINCT attr.value) AS identity_attrs
    
    // Step 3: Find all other orders in the network with the same promocode
    CALL {
      WITH identity_attrs, full_ts
      MATCH (c2:Customer)-[:PLACED]->(o2:Order)-[:HAS_ATTRIBUTE]->(attr2)
      WHERE attr2.value IN identity_attrs
        AND attr2.type IN ['email', 'phone', 'device_id', 'card_details']
        AND o2.promocode = $promocode
        AND datetime(o2.created_at) >= datetime($start)
        AND datetime(o2.created_at) <= datetime($end)
      WITH o2
      ORDER BY o2.created_at ASC
      RETURN COLLECT(o2.created_at) AS sorted_usages
    }
    
    // Step 4: Determine if current order is the first usage or not
    WITH o, order_date, full_ts, sorted_usages,
         CASE WHEN datetime(o.created_at) > datetime(sorted_usages[0]) THEN 1 ELSE 0 END AS is_abusive
    
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

    params = {"promocode": promocode, "start": start_iso, "end": end_iso}


    try:
        with g.neo4j_driver.session() as session_net: 
            result = session_net.run(query, params)
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


@promocode_bp.route("/abuse-history", methods=["GET"])
@login_required
def abuse_history_all_promocodes():
    start_iso, end_iso = get_date_range_from_request(request)

    query_old = """
    MATCH (o:Order)
    WHERE o.promocode IS NOT NULL AND TRIM(o.promocode) <> ""
      AND datetime(o.created_at) >= datetime($start)
      AND datetime(o.created_at) <= datetime($end)
    WITH o.promocode AS promocode, date(datetime(o.created_at)) AS order_date, o
    MATCH (o)-[:HAS_ATTRIBUTE]->(a:Attribute)
    WHERE a.type IN ['email', 'phone', 'device_id', 'card_details']
    WITH promocode, order_date, a.value AS identity, COUNT(DISTINCT o) AS total_for_identity
    WITH promocode, order_date,
         SUM(total_for_identity) AS total_orders,
         SUM(CASE WHEN total_for_identity > 1 THEN total_for_identity - 1 ELSE 0 END) AS abusive_orders
    RETURN 
      promocode,
      order_date,
      total_orders,
      abusive_orders,
      ROUND(abusive_orders * 100.0 / total_orders, 2) AS abuse_rate
    ORDER BY promocode, order_date
    """

    query = """MATCH (c:Customer)-[:PLACED]->(o:Order)
    WHERE o.promocode IS NOT NULL AND TRIM(o.promocode) <> ""
      AND datetime(o.created_at) >= datetime($start)
      AND datetime(o.created_at) <= datetime($end)
    WITH c, o, o.promocode AS promocode, date(datetime(o.created_at)) AS order_date, datetime(o.created_at) AS full_ts
    
    // Collect identity values for this customer
    MATCH (c)-[:PLACED]->(:Order)-[:HAS_ATTRIBUTE]->(attr)
    WHERE attr.type IN ['email', 'phone', 'device_id', 'card_details']
    WITH c, o, promocode, order_date, full_ts, COLLECT(DISTINCT attr.value) AS identity_attrs
    
    // Check if identity used the same promocode before this order
    CALL {
      WITH identity_attrs, full_ts, promocode
      MATCH (c2:Customer)-[:PLACED]->(o2:Order)-[:HAS_ATTRIBUTE]->(attr2)
      WHERE attr2.value IN identity_attrs
        AND attr2.type IN ['email', 'phone', 'device_id', 'card_details']
        AND o2.promocode = promocode
        AND datetime(o2.created_at) < full_ts
         AND datetime(o2.created_at) >= datetime($start)
        AND datetime(o2.created_at) <= datetime($end)
      RETURN COUNT(DISTINCT o2) AS prior_uses
    }
    
    WITH promocode, order_date, COUNT(o) AS total_orders,
         SUM(CASE WHEN prior_uses > 0 THEN 1 ELSE 0 END) AS abusive_orders
    
    RETURN 
      promocode,
      order_date,
      total_orders,
      abusive_orders,
      ROUND(abusive_orders * 100.0 / total_orders, 2) AS abuse_rate
    ORDER BY promocode, order_date"""
    
    try:
        with g.neo4j_driver.session() as session_net:
            result = session_net.run(query, {"start": start_iso, "end": end_iso})
            records = []
            for row in result:
                rec = row.data()
                rec["order_date"] = rec["order_date"].iso_format()
                records.append(rec)
            return jsonify(records), 200
    except Exception as e:
        return jsonify({"error": "Failed to fetch abuse history", "details": str(e)}), 500
