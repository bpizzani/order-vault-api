from flask import Flask, render_template, request, redirect, flash, jsonify
import requests  # For calling the Client App API
from flask_sqlalchemy import SQLAlchemy
from flask_restful import Api, Resource, reqparse 
from flask_migrate import Migrate 
from neo4j import GraphDatabase
import networkx as nx
from order_vault import app
import threading
import time
import hashlib
from flask_cors import CORS
import logging
from order_vault.models.db import db
from order_vault.models.rule import Rule
import os

CORS(app, supports_credentials=True)

# Flask App Setup
app.secret_key = "your_secret_key"
# Database configuration
app.config["SQLALCHEMY_DATABASE_URI"] = 'postgresql://u32cgla1pp9fm7:p6f656fa0f2edb9dda1653485f118f3b8379d957dce3469ef41d13f34d73e8cb1@c5flugvup2318r.cluster-czrs8kj4isg7.us-east-1.rds.amazonaws.com:5432/dc0evnfhnut69e' #os.getenv('DATABASE_URL') #os.environ.get("DATABASE_URL") #"sqlite:///orders_v4.db" #os.environ.get("DATABASE_URL", "sqlite:///orders_v4.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

print(f"Database URI: {os.getenv('DATABASE_URL')}")
db.init_app(app)

#db.create_all()  # This will create tables based on your models

migrate = Migrate(app, db)  # Initialize Flask-Migrate with the app and db

api = Api(app)

# Client App API URL
CLIENT_APP_API_URL = "https://order-vault-client-webapp-13ee822f0ba9.herokuapp.com/api/orders"  # Replace with actual API endpoint

# Neo4j Configuration
NEO4J_URI = "neo4j+s://e027cbe1.databases.neo4j.io"  # Replace with your Neo4j instance URI
NEO4J_USERNAME = "neo4j"  # Replace with your username
NEO4J_PASSWORD = "8qain--QL1kWhww4XY_bKIcoAPgLnexJJt4WC59dRhY"  # Replace with your password
driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))


# Set up logging
logging.basicConfig(level=logging.DEBUG)  # Set level to DEBUG to capture all logs
logger = logging.getLogger(__name__)

@app.route("/", methods=["GET", "POST"])
def home():
    return render_template("home2.html")

@app.route('/rules')
def rules_ui():
    return render_template('rules.html')


@app.route('/promotion_dashboard')
def promotion_ui():
    return render_template('promotion_dashboard.html')

@app.route('/island')
def customer_ui():
    return render_template('island.html')

@app.route("/api/fingerprint", methods=["GET", "POST","OPTIONS"])
def fingerprint():
    if request.method == "OPTIONS":
        # Handle the preflight request (CORS)
        return '', 200

    try:
        logger.info("Received request to /api/fingerprint")

        data = request.json  # Get the raw fingerprint data sent from the client

        if data:
            logger.debug(f"Received data: {data}")
        else:
            logger.warning("No data received in the request")


        # 🔒 Secretly select the features you care about (e.g., userAgent, platform, deviceMemory)
        selected_data = [
            str(data.get("userAgent", "")), 
            str(data.get("platform", "")), 
            str(data.get("screenRes", "")),
            str(data.get("colorDepth", "")),
            str(data.get("timezone", "")),
            str(data.get("languages", "")),
            str(data.get("plugins", "")),
            str(data.get("webGLFingerprint", "")),
            str(data.get("canvasFingerprint", ""))       
        ]

        # 🔑 Generate a unique visitor ID by hashing the selected data
        visitor_id = hashlib.sha256("|".join(selected_data).encode()).hexdigest()

        logger.info(f"Generated visitorId: {visitor_id}")

        return jsonify({"visitorId": visitor_id}), 200

    except Exception as e:
        logger.error(f"Error generating visitorId: {str(e)}")
        return jsonify({"error": "Failed to generate visitorId", "details": str(e)}), 500


# Function to trigger the background process once the order is finalized
def trigger_process_and_update(order_data):
    try:
        #time.sleep(3)  # Simulate some delay

        # Here you would trigger the 'process-and-update' API to process the data
        #process_update_response = requests.get("https://order-vault-api-cb7f5f7bf4f1.herokuapp.com/process-and-update")

        #if process_update_response.status_code == 200:
        #    print("Process and update triggered successfully.")
        #else:
        #    print(f"Error triggering the process-and-update API: {process_update_response.text}")

        # If order was confirmed and fraud evaluation passed, store it in Neo4j
        with driver.session() as session:
            # Here, you can process order_data and save to Neo4j based on the client's confirmation
            save_order_in_neo4j(session, order_data)

    except Exception as e:
        print(f"Error occurred while triggering process-and-update: {str(e)}")


def save_order_in_neo4j(session, order_data):
    """ Save the confirmed order into Neo4j """
    G = nx.Graph()

    order_id = order_data['id']  # Order ID as the main entity
    order_node = f"Order {order_id}"
    G.add_node(order_node, type='order')

    customer_node = f"Customer {order_data['email']}"
    G.add_node(customer_node, type='customer')

    # Link the customer to the order
    G.add_edge(customer_node, order_node)

    # Add order attributes as nodes and edges in the graph
    attributes = ['card_details', 'email', 'device_id', 'phone', 'ip', 'promocode']

    for attribute in attributes:
        attr_value = order_data.get(attribute)
        if attr_value:
            attribute_node = f"{attribute} {attr_value}"
            G.add_node(attribute_node, type=attribute)
            G.add_edge(order_node, attribute_node)  # Connect order to attribute

    # Write the graph to Neo4j
    with session:
        session.write_transaction(create_graph, G)


def create_graph(tx, G):
    """ Helper function to create or update nodes in Neo4j from the NetworkX graph """
    for node_id, node_data in G.nodes(data=True):
        node_label = node_data['type']
        
        # Handling customer nodes
        if node_label == 'customer':
            tx.run("MERGE (c:Customer {email: $email})", email=node_id.split(" ")[1])

        # Handling order nodes
        elif node_label == 'order':
            tx.run("MERGE (o:Order {id: $order_id})", order_id=node_id.split(" ")[1])

        # Handling attribute nodes (card_details, email, device_id, phone, ip, promocode)
        else:
            attr_type, attr_value = node_id.split(" ", 1)
            tx.run("""
            MERGE (a:Attribute {type: $type, value: $value})
            """, type=attr_type, value=attr_value)

        # Establish relationships
        for neighbor in G.neighbors(node_id):
            neighbor_type = G.nodes[neighbor]['type']

            # Link customer to orders
            if neighbor_type == 'order' and node_label == 'customer':
                tx.run("""
                MATCH (c:Customer {email: $email}), (o:Order {id: $order_id})
                MERGE (c)-[:PLACED]->(o)
                """, email=node_id.split(" ")[1], order_id=neighbor.split(" ")[1])

            # Link orders to attributes (ENSURE IT HAPPENS)
            elif node_label == 'order' and neighbor_type in ['card_details', 'email', 'device_id', 'phone', 'ip', 'promocode']:
                tx.run("""
                MATCH (o:Order {id: $order_id})
                MERGE (a:Attribute {type: $type, value: $value})
                MERGE (o)-[:HAS_ATTRIBUTE]->(a)  // Ensure attribute is linked
                """, order_id=node_id.split(" ")[1], type=neighbor_type, value=neighbor.split(" ", 1)[1])

            # Link attributes to each other (cross-linking)
            elif node_label in ['card_details', 'email', 'device_id', 'phone', 'ip', 'promocode'] and neighbor_type in ['card_details', 'email', 'device_id', 'phone', 'ip', 'promocode']:
                tx.run("""
                MATCH (a1:Attribute {type: $type1, value: $value1}), (a2:Attribute {type: $type2, value: $value2})
                MERGE (a1)-[:CONNECTED_TO]->(a2)
                """, type1=node_label, value1=node_id.split(" ", 1)[1], type2=neighbor_type, value2=neighbor.split(" ", 1)[1])
                

# Flask Route to Handle Order Finalization
@app.route("/finalize-order", methods=["POST"])
def finalize_order():
    try:
        # Get order data from the request (client confirms finalization)
        order_data = request.json  # Expecting JSON with order details

        # After client confirms, trigger the background process to handle data processing
        threading.Thread(target=trigger_process_and_update, args=(order_data,)).start()

        return jsonify({"message": "Order finalized and processing started."}), 200

    except Exception as e:
        return jsonify({"error": "An error occurred while finalizing the order", "details": str(e)}), 500



# Flask Route to Process Data and Update Neo4j
@app.route("/process-and-update", methods=["GET"])
def process_and_update():
    try:
        # Fetch data from the Client App API
        client_response = requests.get(CLIENT_APP_API_URL)
        client_response.raise_for_status()
        client_data = client_response.json()["orders"]

        # Create a NetworkX Graph
        G = nx.Graph()

        # Populate the graph with nodes and edges
        for order in client_data:
            customer_node = f"Customer {order['email']}"
            G.add_node(customer_node, type='customer')

            for attribute in ['card_details','email', 'device_id', 'phone', 'promocode', 'id']: # ip_address
                attr_value = order.get(attribute)
                if attr_value:
                    attribute_node = f"{attr_value}"
                    G.add_node(attribute_node, type=attribute)
                    G.add_edge(customer_node, attribute_node)

        # Write the graph to Neo4j
        with driver.session() as session:
            session.write_transaction(create_graph, G)

        return jsonify({"message": "Data processed and graph updated successfully."}), 200

    except requests.exceptions.RequestException as e:
        return jsonify({"error": "Failed to fetch data from Client App API", "details": str(e)}), 500
    except Exception as e:
        return jsonify({"error": "An unexpected error occurred", "details": str(e)}), 500

@app.route("/aggregated-by-attributes", methods=["GET"])
def aggregated_by_attributes():
    try:
        # Get requested attributes (default: "device_id")
        attribute_types = request.args.get("attribute_types", "device_id").split(",") or ["device_id"]
        values = {attr: request.args.get(attr, None) for attr in attribute_types if request.args.get(attr, None)}
        promocode = request.args.get("promocode", None)  # Optional filter

        # 🛠️ FIXED QUERY: Corrected relationships (Orders hold attributes, not Customers)
        query = """
        MATCH (o:Order)-[:HAS_ATTRIBUTE]->(attr:Attribute)
        OPTIONAL MATCH (o)-[:HAS_ATTRIBUTE]->(p:Attribute {type: 'promocode'}) 
        WHERE attr.type IN $attribute_types 
        """

        # Apply optional promocode filtering
        if promocode:
            query += " AND p.value = $promocode"

        query += """
        RETURN 
          attr.type AS attribute_type,
          attr.value AS attribute_value,
          COALESCE(p.value, 'None') AS promocode, 
          COUNT(DISTINCT o.id) AS order_count
        ORDER BY order_count DESC
        """

        params = {"attribute_types": attribute_types}
        if promocode:
            params["promocode"] = promocode

        # Execute the query
        grouped_results = {attr: [] for attr in attribute_types}
        with driver.session() as session:
            neo4j_results = session.run(query, params)
            for record in neo4j_results:
                grouped_results[record["attribute_type"]].append({
                    "attribute_value": record["attribute_value"],
                    "promocode": record["promocode"],
                    "order_count": record["order_count"]
                })

        # Aggregate results
        aggregated_results = {}
        for attribute_type, records in grouped_results.items():
            total_orders = sum(record["order_count"] for record in records)
            aggregated_results[attribute_type] = {
                "order_count": total_orders,
                "promocode": records[0]["promocode"] if records else None
            }

        # 🛠️ FIXED FRAUD CHECK (Now Based on Orders, Not Customers)
        device_order_count = aggregated_results.get("device_id", {}).get("order_count", 0)
        phone_order_count = aggregated_results.get("phone", {}).get("order_count", 0)
        card_order_count = aggregated_results.get("card_details", {}).get("order_count", 0)
        email_order_count = aggregated_results.get("email", {}).get("order_count", 0)

        if device_order_count >= 1 or phone_order_count >= 1 or card_order_count >= 1 or email_order_count >= 1:
            print("🚨 FRAUD DETECTED 🚨")
            return jsonify({"aggregates": "ABUSIVE"}), 200
        else:
            print("✅ GENUINE CUSTOMER ✅")
            return jsonify({"aggregates": "GENUINE"}), 200

    except Exception as e:
        print("Error in /aggregated-by-attributes:", str(e))
        return jsonify({"error": "An unexpected error occurred while fetching aggregates", "details": str(e)}), 500
        
@app.route('/api/rules', methods=['GET', 'POST'])
def manage_rules():
    if request.method == 'POST':
        # Extracting the JSON data from the request
        data = request.json

        # Create a new Rule instance
        new_rule = Rule(attribute=data['attribute'], threshold=data['threshold'], promocode=data['promocode'])

        # Add to database and commit
        db.session.add(new_rule)
        db.session.commit()

        # Return the new rule as JSON (including ID)
        return jsonify({
            "id": new_rule.id,
            "attribute": new_rule.attribute,
            "threshold": new_rule.threshold,
            "promocode": new_rule.promocode
        }), 201  # 201 status means the resource was created successfully

    # GET request: Return all the rules from the database
    rules = Rule.query.all()
    return jsonify([{
        "id": r.id,
        "attribute": r.attribute,
        "threshold": r.threshold,
        "promocode": r.promocode
    } for r in rules])


@app.route('/api/rules/<int:rule_id>', methods=['DELETE'])
def delete_rule(rule_id):
    rule = Rule.query.get(rule_id)
    if rule:
        db.session.delete(rule)
        db.session.commit()
        return jsonify({"message": "Rule deleted successfully"}), 200
    return jsonify({"error": "Rule not found"}), 404


@app.route('/api/evaluate', methods=['GET'])
def evaluate():
    try:
        # Get the attribute types (can be multiple) and values (device_id, phone, etc.) from query parameters
        attribute_types = request.args.get("attribute_types", "device_id").split(",")  # Defaults to "device_id"

        # Get the value for each attribute type (e.g., device_id and phone)
        values = {}
        for attribute_type in attribute_types:
            value = request.args.get(attribute_type, None)
            if value:
                values[attribute_type] = value

        # Get the promocode from the query parameters
        promocode = request.args.get("promocode", None)
        print(f"Promocode to evaluate : {promocode}")

        # Initialize an empty dictionary to store results for each attribute
        evaluation_results = {}

        # Neo4j Query: Aggregate orders by attribute type and promocode
        with driver.session() as session:
            for attribute_type in attribute_types:
                # Base query to match the order attributes
                query = """
                    MATCH (o:Order)-[:HAS_ATTRIBUTE]->(attr:Attribute)
                    WHERE attr.type IN $attribute_types AND attr.value IS NOT NULL
                """
                
                # If promocode is provided, include the promocode condition in the query
                if promocode:
                    query += """
                        MATCH (o)-[:HAS_ATTRIBUTE]->(p:Attribute {type: 'promocode', value: $promocode})
                    """

                # Aggregate the results by attribute type and count the orders
                query += """
                    RETURN attr.type AS attribute_type,
                           attr.value AS attribute_value,
                           COUNT(DISTINCT o.id) AS order_count
                    ORDER BY order_count DESC
                """

                params = {
                    "attribute_types": attribute_types,
                    "promocode": promocode
                }

                # Execute the query and collect results
                results = session.run(query, params)

                # Process the query results into a dictionary
                for record in results:
                    attribute_type = record["attribute_type"]
                    attribute_value = record["attribute_value"]
                    order_count = record["order_count"]

                    # Store the results in the dictionary
                    if attribute_type not in evaluation_results:
                        evaluation_results[attribute_type] = []
                    evaluation_results[attribute_type].append({
                        "attribute_value": attribute_value,
                        "order_count": order_count
                    })

        # Now apply the rules based on the threshold
        final_results = {}
        for attribute_type, records in evaluation_results.items():
            for record in records:
                value = record["attribute_value"]
                count = record["order_count"]

                # Get the rule for the attribute type and promocode
                rule = Rule.query.filter_by(attribute=attribute_type, promocode=promocode).first()
                if not rule:
                    final_results[attribute_type] = {
                        "value": value,
                        "promocode": promocode,
                        "count": count,
                        "abusive": False
                    }
                else:
                    # Compare the count with the rule threshold
                    is_abusive = count >= rule.threshold
                    final_results[attribute_type] = {
                        "value": value,
                        "promocode": promocode,
                        "count": count,
                        "abusive": is_abusive
                    }

        # Determine the overall result (if any attribute is abusive, return overall_abusive as True)
        overall_abusive = any(result["abusive"] for result in final_results.values())
        print("Final Evaluation Results:", final_results)

        return jsonify({"evaluation_results": final_results, "overall_abusive": overall_abusive})

    except Exception as e:
        # Handle unexpected errors
        return jsonify({"error": "An unexpected error occurred", "details": str(e)}), 500

@app.route("/api/customer-attributes-summary", methods=["GET"])
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
        with driver.session() as session:
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
        

@app.route("/api/customer-attributes-network", methods=["GET"])
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
        with driver.session() as session:
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

@app.route("/api/promocode-order-count", methods=["GET"])
def get_promocode_order_count():
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
        with driver.session() as session:
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



@app.route("/api/promocode-usage", methods=["GET"])
def get_promocode_usage():
    promocode = request.args.get("promocode", "").strip()

    # Modified Cypher Query to check abusive usage of the promocode
    query = """
    // Step 1: Find all customers who used the promocode
    MATCH (c:Customer)-[:PLACED]->(order:Order)-[:HAS_ATTRIBUTE]->(promocode_attr:Attribute {value: $promocode, type: 'promocode'})
    WITH c, order
    
    // Step 2: Collect shared attributes (email, phone, device_id, card_details) for the customer
    MATCH (c)-[:PLACED]->(order)-[:HAS_ATTRIBUTE]->(attr)
    WHERE attr.type IN ['phone', 'device_id', 'card_details', 'email']
    WITH c, COLLECT(DISTINCT attr.value) AS shared_attributes, order
    
    // Step 3: Find other customers linked by shared attributes (device, card details, phone, email)
    MATCH (c2:Customer)-[:PLACED]->(order2:Order)-[:HAS_ATTRIBUTE]->(attr2)
    WHERE attr2.value IN shared_attributes AND attr2.type IN ['phone', 'device_id', 'card_details', 'email']
    
    // Step 4: Count how many times the linked customers have used the promocode (same promocode used by both c and c2)
    MATCH (c2)-[:PLACED]->(order2:Order)-[:HAS_ATTRIBUTE]->(promocode_attr2:Attribute {value: $promocode, type: 'promocode'})
    WITH c, c2, COUNT(DISTINCT order2.id) AS connected_orders, COLLECT(DISTINCT order2.id) AS all_order_ids
    
    // Step 5: Flag networks as abusive if connected orders > 1 (indicating a link between multiple orders with the same promocode)
    WITH c, c2, connected_orders, all_order_ids,
         CASE WHEN connected_orders > 1 THEN 1 ELSE 0 END AS abusive
    
    // Step 6: Aggregate total usage of the promocode
    MATCH (order)-[:HAS_ATTRIBUTE]->(promocode_attr:Attribute {value: $promocode, type: 'promocode'})
    WITH c, COUNT(DISTINCT order.id) AS total_orders, abusive, all_order_ids
    
    // Step 7: Aggregate abusive orders and total orders for abuse rate, focusing on connections via device, card details, etc.
    WITH c, COUNT(DISTINCT all_order_ids) AS total_usage_count, 
         COUNT(DISTINCT CASE WHEN abusive = 1 THEN all_order_ids END) AS abusive_usage_count
    
    // Step 8: Calculate total abuse rate for the promotion
    WITH COUNT(distinct c.email) AS total_usage, SUM(abusive_usage_count) AS abusive_usage_count
    RETURN 
        total_usage, 
        abusive_usage_count,
        (abusive_usage_count * 100.0 / total_usage) AS abuse_rate_percentage"""
    

    params = {"promocode": promocode} if promocode else {}

    try:
        with driver.session() as session:
            result = session.run(query, params)
            records = [record.data() for record in result]

            if records:
                return jsonify(records), 200
            else:
                return jsonify({"message": "No data found for this promocode"}), 200

    except Exception as e:
        return jsonify({"error": "Database error", "details": str(e)}), 500
        
if __name__ == "__main__":
    print("started APP")
    #app.run(debug=True, port=5002)  # Run the Middle App on a different port
