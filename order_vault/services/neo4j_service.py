from neo4j import Session
from flask import Blueprint, request, jsonify, current_app, g
import networkx as nx
from .network_graph import build_graph_from_order



# Function to trigger the background process once the order is finalized
def trigger_process_and_update(order_data,neo4j_driver):
    try:
        #time.sleep(3)  # Simulate some delay

        # Here you would trigger the 'process-and-update' API to process the data
        #process_update_response = requests.get("https://order-vault-api-cb7f5f7bf4f1.herokuapp.com/process-and-update")

        #if process_update_response.status_code == 200:
        #    print("Process and update triggered successfully.")
        #else:
        #    print(f"Error triggering the process-and-update API: {process_update_response.text}")
        driver = neo4j_driver
        # If order was confirmed and fraud evaluation passed, store it in Neo4j
        with driver.session() as session:
            # Here, you can process order_data and save to Neo4j based on the client's confirmation
            save_order_in_neo4j(session, order_data)

    except Exception as e:
        print(f"Error occurred while triggering process-and-update: {str(e)}")


def save_order_in_neo4j(session, order_data):
    """ Save the confirmed order into Neo4j """
    print(f"[NEO4J] save_order_in_neo4j called with order_id: {order_data.get('id')}")
    print(f"[NEO4J] order_data keys: {list(order_data.keys())}")
    
    G = nx.Graph()

    order_id = order_data['id']
    order_node = f"Order {order_id}"

    G.add_node(order_node,
               type='order',
               created_at=order_data.get('created_at'),
               promocode=(order_data.get("coupon") or {}).get("promocode"),
               promotion_id=(order_data.get("coupon") or {}).get("promotion_id"),
               call_type=order_data.get('call_type')
              )

    customer_node = f"Customer {order_data['email']}"
    G.add_node(customer_node, type='customer', user_id=order_data.get('user_id'))
    G.add_edge(customer_node, order_node)

    attributes = ['card_details', 'email', 'device_id', 'phone', 'local_session_id']
    for attribute in attributes:
        attr_value = order_data.get(attribute)
        print(f"[NEO4J] attribute '{attribute}': {attr_value}")
        if attr_value:
            attribute_node = f"{attribute} {attr_value}"
            G.add_node(attribute_node, type=attribute)
            G.add_edge(order_node, attribute_node)

    print(f"[NEO4J] Graph nodes ({G.number_of_nodes()}): {list(G.nodes())}")
    print(f"[NEO4J] Graph edges ({G.number_of_edges()}): {list(G.edges())}")

    try:
        print(f"[NEO4J] Starting execute_write...")
        with session:
            session.execute_write(create_graph, G)
        print(f"[NEO4J] execute_write completed successfully")
    except Exception as e:
        print(f"[NEO4J] ERROR in execute_write: {type(e).__name__}: {str(e)}")
        raise


def create_graph(tx, G):
    """Create or update nodes and relationships in Neo4j from the NetworkX graph"""
    print(f"[NEO4J] create_graph transaction started")

    # --- Step 1: Create all nodes first ---
    print(f"[NEO4J] Step 1: Creating nodes...")
    for node_id, node_data in G.nodes(data=True):
        node_label = node_data['type']
        print(f"[NEO4J]   Processing node: '{node_id}' (type={node_label})")

        if node_label == 'customer':
            email = node_id.split(" ", 1)[1]
            user_id = node_data.get('user_id')
            print(f"[NEO4J]   MERGE Customer email={email}, user_id={user_id}")
            tx.run("""MERGE (c:Customer {email: $email})
                    SET c.user_id = $user_id""", email=email, user_id=user_id)

        elif node_label == 'order':
            order_id   = node_id.split(" ", 1)[1]
            created_at = node_data.get('created_at')
            promocode  = node_data.get('promocode')
            promotion_id = node_data.get('promotion_id')
            call_type  = node_data.get('call_type')
            print(f"[NEO4J]   MERGE Order id={order_id}, created_at={created_at}, promocode={promocode}")
            tx.run(
                """
                MERGE (o:Order {id:$order_id})
                SET o.created_at = $created_at,
                    o.promocode = $promocode,
                    o.promotion_id = $promotion_id,
                    o.call_type = $call_type
                """,
                order_id=order_id,
                created_at=created_at,
                promocode=promocode,
                promotion_id=promotion_id,
                call_type=call_type
            )

        else:
            attr_type, attr_value = node_id.split(" ", 1)
            print(f"[NEO4J]   MERGE Attribute type={attr_type}, value={attr_value}")
            tx.run(
                "MERGE (a:Attribute {type: $type, value: $value})",
                type=attr_type,
                value=attr_value
            )

    # --- Step 2: Create all relationships ---
    print(f"[NEO4J] Step 2: Creating relationships...")
    for node_id in G.nodes():
        node_label = G.nodes[node_id]['type']

        for neighbor in G.neighbors(node_id):
            neighbor_label = G.nodes[neighbor]['type']
            print(f"[NEO4J]   Edge: '{node_id}' ({node_label}) → '{neighbor}' ({neighbor_label})")

            if node_label == 'customer' and neighbor_label == 'order':
                email    = node_id.split(" ", 1)[1]
                order_id = neighbor.split(" ", 1)[1]
                print(f"[NEO4J]   MERGE (Customer:{email})-[:PLACED]->(Order:{order_id})")
                tx.run(
                    """
                    MATCH (c:Customer {email: $email}), (o:Order {id: $order_id})
                    MERGE (c)-[:PLACED]->(o)
                    """,
                    email=email,
                    order_id=order_id
                )

            elif node_label == 'order' and neighbor_label not in ['order', 'customer']:
                order_id  = node_id.split(" ", 1)[1]
                attr_type = neighbor_label
                attr_value = neighbor.split(" ", 1)[1]
                print(f"[NEO4J]   MERGE (Order:{order_id})-[:HAS_ATTRIBUTE]->(Attribute:{attr_type}={attr_value})")
                tx.run(
                    """
                    MATCH (o:Order {id: $order_id}), 
                          (a:Attribute {type: $type, value: $value})
                    MERGE (o)-[:HAS_ATTRIBUTE]->(a)
                    """,
                    order_id=order_id,
                    type=attr_type,
                    value=attr_value
                )

                # 3) Attribute → CONNECTED_TO → Attribute
            #elif node_label not in ['order', 'customer'] and neighbor_label not in ['order', 'customer'] and node_label != 'promocode' and neighbor_label != 'promocode':
            #    tx.run(
            #        """
            #        MATCH (a1:Attribute {type: $type1, value: $value1}),
            #              (a2:Attribute {type: $type2, value: $value2})
            #        MERGE (a1)-[:CONNECTED_TO]->(a2)
            #        """,
            #        type1=node_label,
            #        value1=node_id.split(" ", 1)[1],
            #        type2=neighbor_label,
            #        value2=neighbor.split(" ", 1)[1]
            #    )

    # --- Step 3: Customer → HAS_ATTRIBUTE ---
    print(f"[NEO4J] Step 3: Linking Customer HAS_ATTRIBUTE via orders...")
    tx.run(
        """
        MATCH (c:Customer)-[:PLACED]->(o:Order)-[:HAS_ATTRIBUTE]->(a:Attribute)
        WHERE a.type <> 'promocode' 
        MERGE (c)-[:HAS_ATTRIBUTE]->(a)
        """
    )
    print(f"[NEO4J] create_graph transaction completed")
    

def evaluate_attributes(session: Session, attribute_types: list, promocode: str = None) -> dict:
    """
    Aggregate order counts by attribute types (and optional promocode). Returns a dict:
        { attribute_type: [ {attribute_value, order_count}, ... ], ... }
    """
    parts = [
        "MATCH (o:Order)-[:HAS_ATTRIBUTE]->(attr:Attribute)",
        "WHERE attr.type IN $types"
    ]
    params = {"types": attribute_types}

    if promocode:
        parts.append("AND o.promocode = $promocode")
        params["promocode"] = promocode

    parts.append(
        "RETURN attr.type AS attribute_type,"
        " attr.value AS attribute_value,"
        " COUNT(DISTINCT o.id) AS order_count"
        " ORDER BY order_count DESC"
    )
    query = "\n".join(parts)

    result = session.run(query, params)
    raw = {}
    for rec in result:
        at = rec["attribute_type"]
        raw.setdefault(at, []).append({
            "attribute_value": rec["attribute_value"],
            "order_count": rec["order_count"]
        })
    return raw
    
def evaluate_attributes_v3(session: Session, attribute_types: list, promocode: str = None) -> dict:
    # Optimized Cypher with direct node property filtering
    if promocode:
        query = """
        MATCH (o:Order {promocode: $promocode})-[:HAS_ATTRIBUTE]->(attr:Attribute)
        WHERE attr.type IN $types
        RETURN attr.type AS attribute_type,
               attr.value AS attribute_value,
               COUNT(*) AS order_count
        ORDER BY order_count DESC
        """
        params = {"types": attribute_types, "promocode": promocode}
    else:
        query = """
        MATCH (o:Order)-[:HAS_ATTRIBUTE]->(attr:Attribute)
        WHERE attr.type IN $types
        RETURN attr.type AS attribute_type,
               attr.value AS attribute_value,
               COUNT(*) AS order_count
        ORDER BY order_count DESC
        """
        params = {"types": attribute_types}

    # Run query and build result
    result = session.run(query, params)
    output = {}
    for record in result:
        output.setdefault(record["attribute_type"], []).append({
            "attribute_value": record["attribute_value"],
            "order_count": record["order_count"]
        })

    return output
    
def evaluate_attributes_olv_v2(session: Session, attribute_types: list, promocode: str = None) -> dict:
    query = """
    MATCH (o:Order)-[:HAS_ATTRIBUTE]->(attr:Attribute)
    WHERE attr.type IN $types {promo_clause}
    RETURN attr.type AS attribute_type,
           attr.value AS attribute_value,
           COUNT(DISTINCT o) AS order_count
    ORDER BY order_count DESC
    """

    params = {"types": attribute_types}
    if promocode:
        query = query.replace("{promo_clause}", "AND o.promocode = $promocode")
        params["promocode"] = promocode
    else:
        query = query.replace("{promo_clause}", "")

    result = session.run(query, params)
    output = {}
    for record in result:
        output.setdefault(record["attribute_type"], []).append({
            "attribute_value": record["attribute_value"],
            "order_count": record["order_count"]
        })

    return output
    


def evaluate_attributes_deprecated(session: Session, attribute_types: list, promocode: str = None) -> dict:
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

