
from flask import Flask, request, jsonify
import requests  # For calling the Client App API
from neo4j import GraphDatabase
import networkx as nx
from order_vault import app
import threading
import time

# Flask App Setup
app.secret_key = "your_secret_key"
# Client App API URL
CLIENT_APP_API_URL = "https://order-vault-client-webapp-13ee822f0ba9.herokuapp.com/api/orders"  # Replace with actual API endpoint

# Neo4j Configuration
NEO4J_URI = "neo4j+s://e027cbe1.databases.neo4j.io"  # Replace with your Neo4j instance URI
NEO4J_USERNAME = "neo4j"  # Replace with your username
NEO4J_PASSWORD = "8qain--QL1kWhww4XY_bKIcoAPgLnexJJt4WC59dRhY"  # Replace with your password
driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))

# Helper Function to Create Neo4j Graph from NetworkX Graph
def create_graph(tx, G):
    for node_id, node_data in G.nodes(data=True):
        if node_data['type'] == 'customer':
            # Create or merge the Customer node
            tx.run("MERGE (c:Customer {email: $email, type:'customer'})", email=node_id)
        for neighbor in G.neighbors(node_id):
            if node_data['type'] == 'customer':
                # Create relationship from customer to attribute
                tx.run("""
                MERGE (c:Customer {email: $email, type:"customer"})
                MERGE (a {value: $value, type:$type})
                MERGE (c)-[:HAS_ATTRIBUTE]->(a)
                """, email=node_id, value=neighbor, type=G.nodes[neighbor]['type'])
            else:
                # Create relationships between attributes
                if G.nodes[neighbor]['type'] != 'customer':
                    tx.run("""
                    MERGE (a1 {value: $value1, type:$type})
                    MERGE (a2 {value: $value2, type:$type})
                    MERGE (a1)-[:CONNECTED_TO]->(a2)
                    """, value1=node_id, value2=neighbor, type=G.nodes[neighbor]['type'])


def update_graph_incrementally(tx, G_new):
    # Create or update nodes based on their unique identifier and type
    for node, attributes in G_new.nodes(data=True):
        node_type = attributes.get('type', 'unknown')  # Ensure type is always set
        tx.run(
            """
            MERGE (n:Node {id: $id, type: $type})
            SET n.type = $type
            """,
            id=node,
            type=node_type
        )

    # Create or update relationships between nodes
    for u, v in G_new.edges():
        # Get the types of the nodes for each relationship (use the node type)
        type_u = G_new.nodes[u]['type']
        type_v = G_new.nodes[v]['type']

        # If both nodes are customers, create a 'HAS_ATTRIBUTE' relationship
        if type_u == 'customer' and type_v != 'customer':
            tx.run(
                """
                MATCH (a:Node {id: $u}), (b:Node {id: $v})
                MERGE (a)-[:HAS_ATTRIBUTE]->(b)
                """,
                u=u,
                v=v
            )
        elif type_v == 'customer' and type_u != 'customer':
            tx.run(
                """
                MATCH (a:Node {id: $u}), (b:Node {id: $v})
                MERGE (b)-[:HAS_ATTRIBUTE]->(a)
                """,
                u=u,
                v=v
            )
        else:
            # For other types of relationships, use 'CONNECTED_TO'
            tx.run(
                """
                MATCH (a:Node {id: $u}), (b:Node {id: $v})
                MERGE (a)-[:CONNECTED_TO]->(b)
                """,
                u=u,
                v=v
            )
            
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

            for attribute in ['ip_address', 'card_details','email', 'device_id', 'phone', 'promocode', 'id']:
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

# Flask Route to Incrementally Update Neo4j Graph with t-1 Data
@app.route("/process-and-update-increment", methods=["GET"])
def process_and_update_increment():
    try:
        # Fetch only t-1 data from the Client App API
        t_minus_1_data_url = f"{CLIENT_APP_API_URL}"
        client_response = requests.get(t_minus_1_data_url)
        client_response.raise_for_status()
        t1_data = client_response.json()["orders"]

        # Create a NetworkX Graph for the new data
        G_new = nx.Graph()

        # Populate the graph with nodes and edges for t-1
        for order in t1_data:
            customer_node = f"Customer {order['email']}"
            G_new.add_node(customer_node, type='customer')

            for attribute in ['ip_address', 'card_details', 'email', 'device_id', 'phone', 'promocode', 'id']:
                attr_value = order.get(attribute)
                if attr_value:
                    attribute_node = f"{attr_value}"
                    G_new.add_node(attribute_node, type=attribute)
                    G_new.add_edge(customer_node, attribute_node)

        # Write only the new data to Neo4j
        with driver.session() as session:
            session.write_transaction(update_graph_incrementally, G_new)

        return jsonify({"message": "Graph updated successfully with t-1 data."}), 200

    except requests.exceptions.RequestException as e:
        return jsonify({"error": "Failed to fetch data from Client App API", "details": str(e)}), 500
    except Exception as e:
        return jsonify({"error": "An unexpected error occurred", "details": str(e)}), 500
        

def trigger_process_and_update():
    try:
        # Delay the execution for 30 seconds (you can change this value)
        time.sleep(5) 
        
        # Make the request to the /process-and-update route
        process_update_response = requests.get("https://order-vault-api-cb7f5f7bf4f1.herokuapp.com/process-and-update")
        
        if process_update_response.status_code == 200:
            print("Process and update triggered successfully.")
        else:
            print(f"Error triggering the process-and-update API: {process_update_response.text}")
    except Exception as e:
        print(f"Error occurred while triggering /process-and-update: {str(e)}")
        
@app.route("/aggregated-by-attributes-old", methods=["GET"])
def aggregated_by_attributes_old(): #deprecated
    try:
        # Get the attribute type and optional filters (phone, device_id) from the query parameters
        attribute_type = request.args.get("attribute_type", "device_id")  # Default to 'device_id'
        value = request.args.get("value", None)  # Optional filter by phone
        promocode = request.args.get("promocode", None)  # Optional filter by promocode
        
        # Neo4j query to aggregate data by attribute + promocode, with optional filters
        query = """
        MATCH (c:Customer)-[:HAS_ATTRIBUTE]->(attr {type: $attribute_type})
        MATCH (c)-[:HAS_ATTRIBUTE]->(p {type: 'promocode'})
        WHERE attr.value IS NOT NULL AND p.value IS NOT NULL
        """
        
        # Add filtering based on phone or device_id if provided
        if value:
            query += " AND attr.value = $value"
            query += " AND p.value = $promocode"
        
        query += """
        RETURN 
          attr.value AS attribute_value,
          p.value AS promocode,
          COUNT(DISTINCT c.email) AS customer_count
        ORDER BY customer_count DESC
        """
        
        # Prepare parameters for Neo4j query
        params = {"attribute_type": attribute_type}
        if value:
            params["value"] = value
            params["promocode"] = promocode
            
        results = []
        
        # Execute the query
        with driver.session() as session:
            neo4j_results = session.run(query, params)
            for record in neo4j_results:
                results.append({
                    "attribute_value": record["attribute_value"],
                    "promocode": record["promocode"],
                    "customer_count": record["customer_count"]
                })
                
        # Update network graphs for next time.
        # Trigger the process-and-update function in the background with a delay
        threading.Thread(target=trigger_process_and_update).start()
        return jsonify({"aggregates": results}), 200

    except Exception as e:
        return jsonify({"error": "An unexpected error occurred while fetching aggregates", "details": str(e)}), 500

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
        threading.Thread(target=trigger_process_and_update).start()
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
        

if __name__ == "__main__":
    print("started APP")
    #app.run(debug=True, port=5002)  # Run the Middle App on a different port
