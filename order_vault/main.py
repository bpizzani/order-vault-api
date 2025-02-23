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

@app.route("/api/customer-attributes", methods=["GET"])
def get_customer_attributes():
    email = request.args.get("email", "").strip().lower()  # Normalize input

    if not email:
        return jsonify({"error": "Missing email parameter"}), 400

    print(f"Received email: {email}")  # Add this to check what email is received

    query = """
    MATCH (c:Customer {email: $email})-[:HAS_ATTRIBUTE]->(attr)
    RETURN attr.type AS attribute, COUNT(attr) AS count
    """

    params = {"email": email}

    try:
        with driver.session() as session:
            result = session.run(query, params)
            attributes = {record["attribute"]: record["count"] for record in result}

        if not attributes:
            return jsonify({"message": "No attributes found for this email"}), 200

        return jsonify(attributes), 200

    except Exception as e:
        return jsonify({"error": "Database error", "details": str(e)}), 500
        
    
@app.route("/", methods=["GET", "POST"])
def home():
    return render_template("home.html")

@app.route('/rules')
def rules_ui():
    return render_template('rules.html')

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

    customer_node = f"Customer {order_data['email']}"
    G.add_node(customer_node, type='customer')

    # Add order attributes as nodes and edges in the graph
    for attribute in ['card_details', 'email', 'device_id', 'phone', 'promocode', 'id']:
        attr_value = order_data.get(attribute)
        if attr_value:
            attribute_node = f"{attr_value}"
            G.add_node(attribute_node, type=attribute)
            G.add_edge(customer_node, attribute_node)

    # Write the graph to Neo4j
    with session:
        session.write_transaction(create_graph, G)


def create_graph(tx, G):
    """ Helper function to create or update nodes in Neo4j from the NetworkX graph """
    for node_id, node_data in G.nodes(data=True):
        if node_data['type'] == 'customer':
            tx.run("MERGE (c:Customer {email: $email, type:'customer'})", email=node_id)

        for neighbor in G.neighbors(node_id):
            if node_data['type'] == 'customer':
                tx.run("""
                MERGE (c:Customer {email: $email, type:"customer"})
                MERGE (a {value: $value, type:$type})
                MERGE (c)-[:HAS_ATTRIBUTE]->(a)
                """, email=node_id, value=neighbor, type=G.nodes[neighbor]['type'])
            else:
                if G.nodes[neighbor]['type'] != 'customer':
                    tx.run("""
                    MERGE (a1 {value: $value1, type:$type})
                    MERGE (a2 {value: $value2, type:$type})
                    MERGE (a1)-[:CONNECTED_TO]->(a2)
                    """, value1=node_id, value2=neighbor, type=G.nodes[neighbor]['type'])


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
        # Get the attribute types (can be multiple) and optional filters (phone, device_id) from the query parameters
        attribute_types = request.args.get("attribute_types", "device_id").split(",")  # Defaults to "device_id"

        # Get the value for each attribute type (e.g., device_id and phone)
        values = {}
        for attribute_type in attribute_types:
            value = request.args.get(attribute_type, None)
            if value:
                values[attribute_type] = value

        promocode = request.args.get("promocode", None)  # Optional filter by promocode

        # Initialize an empty dictionary to store the results grouped by attribute type
        grouped_results = {attribute_type: [] for attribute_type in attribute_types}

        # Neo4j query to aggregate data by attribute + promocode, with optional filters
        for attribute_type in attribute_types:
            query = """
            MATCH (c:Customer)-[:HAS_ATTRIBUTE]->(attr {type: $attribute_type})
            MATCH (c)-[:HAS_ATTRIBUTE]->(p {type: 'promocode'})
            WHERE attr.value IS NOT NULL AND p.value IS NOT NULL
            """

            # Add filtering based on value (phone, device_id) if provided
            if attribute_type in values:
                query += f" AND attr.value = ${attribute_type}"
                query += " AND p.value = $promocode"

            query += """
            RETURN 
              attr.value AS attribute_value,
              p.value AS promocode,
              COUNT(DISTINCT c.email) AS customer_count
            ORDER BY customer_count DESC
            """

            # Prepare parameters for Neo4j query
            params = {"attribute_type": attribute_type, "promocode": promocode}
            if attribute_type in values:
                params[attribute_type] = values[attribute_type]

            # Execute the query
            with driver.session() as session:
                neo4j_results = session.run(query, params)
                for record in neo4j_results:
                    grouped_results[attribute_type].append({
                        "attribute_value": record["attribute_value"],
                        "promocode": record["promocode"],
                        "customer_count": record["customer_count"]
                    })

        # Trigger background process for next time
        aggregated_results = {attribute_type: [] for attribute_type in attribute_types}

        # Group the aggregated data by attribute type
        for k,aggregate in grouped_results.items():
            if len(aggregate) > 0:
                aggregate = aggregate[0]
                attribute_type = k
                aggregated_results[attribute_type].append({
                    "attribute_value": aggregate["attribute_value"],
                    "promocode": aggregate["promocode"],
                    "customer_count": aggregate["customer_count"]
                })

         # Get aggregated data 
        aggregated_device_data = aggregated_results.get("device_id", [])[0] if "device_id" in aggregated_results and len(aggregated_results["device_id"]) > 0 else None
        aggregated_phone_data = aggregated_results.get("phone", [])[0] if "phone" in aggregated_results and len(aggregated_results["phone"]) > 0 else None
        aggregated_card_data = aggregated_results.get("card_details", [])[0] if "card_details" in aggregated_results and len(aggregated_results["card_details"]) > 0 else None
        aggregated_email_data = aggregated_results.get("email", [])[0] if "email" in aggregated_results and len(aggregated_results["email"]) > 0 else None

        # Extract the customer count for each, defaulting to 0 if not available
        device_customer_count = aggregated_device_data["customer_count"] if aggregated_device_data else 0
        phone_customer_count = aggregated_phone_data["customer_count"] if aggregated_phone_data else 0
        card_customer_count = aggregated_card_data["customer_count"] if aggregated_card_data else 0
        email_customer_count = aggregated_email_data["customer_count"] if aggregated_email_data else 0

        #threading.Thread(target=trigger_process_and_update).start()

        if device_customer_count >= 1 or phone_customer_count >= 1 or card_customer_count >= 1 or email_customer_count >= 1:
            print("FRAUD")
            return jsonify({"aggregates": "ABUSIVE"}), 200
        else:
            print("GENUINE")
            return jsonify({"aggregates": "GENUINE"}), 200
        # Return the aggregated results grouped by attribute type
        #return jsonify({"aggregates": grouped_results}), 200

    except Exception as e:
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

        # Iterate over the attribute types and evaluate based on the rules
        for attribute_type in attribute_types:
            # Get the rule for the attribute type
            rule = Rule.query.filter_by(attribute=attribute_type,promocode=promocode).first()
            print(f"Rule to evaluate : {rule}")
            # If no rule is found, log it and proceed with a default threshold (e.g., 0)
            if not rule:
                print(f"No rule found for attribute {attribute_type}.")
                evaluation_results[attribute_type] = {
                    "value": values.get(attribute_type),
                    "promocode": promocode,
                    "count": 0,
                    "abusive": False
                }
            else:
                # Query Neo4j to count occurrences of the attribute value + promocode
                with driver.session() as session:

                    query = """
                        MATCH (c:Customer)-[:HAS_ATTRIBUTE]->(attr {type: $attribute_type, value: $value})
                        """
                    if promocode:
                        query += "MATCH (c)-[:HAS_ATTRIBUTE]->(p {type: 'promocode', value: $promocode})"
                    query += "RETURN COUNT(DISTINCT c.email) AS count"
                    
                    result = session.run(query, attribute_type=attribute_type, value=values.get(attribute_type), promocode=promocode)

                    # Safeguard in case no result is returned
                    count = result.single()["count"] if result else 0

                # Compare the count with the rule threshold
                is_abusive = count >= rule.threshold
                evaluation_results[attribute_type] = {
                    "value": values.get(attribute_type),
                    "promocode": promocode,
                    "count": count,
                    "abusive": is_abusive
                }

        # Determine the overall result (if any attribute is abusive, return overall_abusive as True)
        overall_abusive = any(result["abusive"] for result in evaluation_results.values())
        print(evaluation_results)
        return jsonify({"evaluation_results": evaluation_results, "overall_abusive": overall_abusive})

    except Exception as e:
        return jsonify({"error": "An unexpected error occurred", "details": str(e)}), 500


if __name__ == "__main__":
    print("started APP")
    #app.run(debug=True, port=5002)  # Run the Middle App on a different port
