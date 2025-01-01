
from flask import Flask, request, jsonify
import requests  # For calling the Client App API
from neo4j import GraphDatabase
import networkx as nx
from order_vault import app


# Flask App Setup
app = Flask(__name__)

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


@app.route("/aggregated-by-attributes", methods=["GET"])
def aggregated_by_attributes():
    try:
        # Neo4j query to aggregate data by attribute + promocode
        query = """
        MATCH (c:Customer)-[:HAS_ATTRIBUTE]->(attr {type: $attribute_type})
        MATCH (c)-[:HAS_ATTRIBUTE]->(p {type: 'promocode'})
        WHERE attr.value IS NOT NULL AND p.value IS NOT NULL
        RETURN 
          attr.value AS attribute_value,
          p.value AS promocode,
          COUNT(DISTINCT c.email) AS customer_count
        ORDER BY customer_count DESC
        """
        
        # Get the attribute type from the query parameters (e.g., 'device_id', 'phone')
        attribute_type = request.args.get("attribute_type", "device_id")
        
        results = []
        
        # Execute the query
        with driver.session() as session:
            neo4j_results = session.run(query, attribute_type=attribute_type)
            for record in neo4j_results:
                results.append({
                    "attribute_value": record["attribute_value"],
                    "promocode": record["promocode"],
                    "customer_count": record["customer_count"]
                })
        
        return jsonify({"aggregates": results}), 200

    except Exception as e:
        return jsonify({"error": "An unexpected error occurred while fetching aggregates", "details": str(e)}), 500


if __name__ == "__main__":
    #app.run(debug=True, port=5002)  # Run the Middle App on a different port
