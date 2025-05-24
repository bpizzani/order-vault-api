from neo4j import Session
from flask import Blueprint, request, jsonify, current_app
import networkx as nx
from .network_graph import build_graph_from_order



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
        driver = current_app.neo4j_driver
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

    # add order node with created_at
    G.add_node(order_node,
               type='order',
               created_at=order_data.get('created_at'))

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
    """
    Merge nodes and relationships in Neo4j from the NetworkX graph.
    Then create customer-to-customer links based on shared attributes of this order.
    """
    # --- Step 1: Merge nodes ---
    for node_id, data in G.nodes(data=True):
        label = data['type']
        if label == 'customer':
            _, email = node_id.split(' ', 1)
            tx.run("MERGE (c:Customer {email:$email})", email=email)

        elif label == 'order':
            _, oid = node_id.split(' ', 1)
            tx.run(
                """
                MERGE (o:Order {id:$oid})
                SET o.created_at = $created_at
                """,
                oid=oid,
                created_at=data.get('created_at')
            )

        else:
            t, v = node_id.split(' ', 1)
            tx.run(
                "MERGE (a:Attribute {type:$t, value:$v})",
                t=t, v=v
            )

    # --- Step 2: Merge order and attribute relationships ---
    for u, v in G.edges():
        ut = G.nodes[u]['type']
        vt = G.nodes[v]['type']

        if ut == 'customer' and vt == 'order':
            _, email = u.split(' ', 1)
            _, order_id = v.split(' ', 1)
            tx.run(
                "MATCH (c:Customer{email:$email}), (o:Order{id:$order_id}) MERGE (c)-[:PLACED]->(o)",
                email=email, order_id=order_id
            )

        elif ut == 'order' and vt not in ('order', 'customer'):
            _, order_id = u.split(' ', 1)
            t = vt
            _, val = v.split(' ', 1)
            tx.run(
                "MATCH (o:Order{id:$order_id}), (a:Attribute{type:$t,value:$val}) \
                 MERGE (o)-[:HAS_ATTRIBUTE]->(a)",
                order_id=order_id, t=t, val=val
            )


    # --- Step 3: Create direct customer-to-customer relationships when they share attributes ---
    for node_id, data in G.nodes(data=True):
        if data['type'] not in ('order', 'customer'):
            attr_type, attr_value = node_id.split(' ', 1)
            tx.run(
                """
                // find all customers who placed any order with this attribute
                MATCH (c1:Customer)-[:PLACED]->(:Order)-[:HAS_ATTRIBUTE]->(a:Attribute {type:$type, value:$value})
                MATCH (c2:Customer)-[:PLACED]->(:Order)-[:HAS_ATTRIBUTE]->(a)
                WHERE c1.email <> c2.email
                MERGE (c1)-[r:LINKED_TO {attributeType:$type, attributeValue:$value}]->(c2)
                """,
                type=attr_type,
                value=attr_value
            )
        
def evaluate_attributes(session: Session, attribute_types: list, promocode: str = None) -> dict:
    """
    Aggregate order counts by attribute types (and optional promocode). Returns a dict:
        { attribute_type: [ {attribute_value, order_count}, ... ], ... }
    """
    # Build Cypher query
    parts = [
        "MATCH (o:Order)-[:HAS_ATTRIBUTE]->(attr:Attribute)",
        "WHERE attr.type IN $types"
    ]
    params = {"types": attribute_types}
    if promocode:
        parts.append(
            "AND exists((o)-[:HAS_ATTRIBUTE]->(:Attribute {type: 'promocode', value: $promocode}))"
        )
        params["promocode"] = promocode

    parts.append(
        "RETURN attr.type AS attribute_type,"
        " attr.value AS attribute_value,"
        " COUNT(DISTINCT o.id) AS order_count"
        " ORDER BY order_count DESC"
    )
    query = "\n".join(parts)

    # Execute query
    result = session.run(query, params)
    raw = {}
    for rec in result:
        at = rec["attribute_type"]
        raw.setdefault(at, []).append({
            "attribute_value": rec["attribute_value"],
            "order_count": rec["order_count"]
        })
    return raw

