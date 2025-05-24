from neo4j import Session
from .network_graph import build_graph_from_order


def save_order_graph(session: Session, order_data: dict) -> None:
    """
    Build a NetworkX graph from order_data and write it to Neo4j in a single transaction.
    """
    G = build_graph_from_order(order_data)
    session.write_transaction(_create_graph_tx, G)


def _create_graph_tx(tx, G):
    """
    Transaction function to MERGE nodes and relationships in Neo4j from a NetworkX Graph.
    """
    # Merge nodes
    for node_id, data in G.nodes(data=True):
        label = data.get('type')

        if label == 'customer':
            _, email = node_id.split(' ', 1)
            tx.run(
                "MERGE (c:Customer {email: $email})",
                email=email
            )

        elif label == 'order':
            _, order_id = node_id.split(' ', 1)
            tx.run(
                "MERGE (o:Order {id: $order_id})",
                order_id=order_id
            )

        else:
            # attribute nodes
            attr_type = label
            _, value = node_id.split(' ', 1)
            tx.run(
                "MERGE (a:Attribute {type: $type, value: $value})",
                type=attr_type,
                value=value
            )

    # Merge relationships
    for u, v in G.edges():
        u_type = G.nodes[u]['type']
        v_type = G.nodes[v]['type']

        if u_type == 'customer' and v_type == 'order':
            _, email = u.split(' ', 1)
            _, order_id = v.split(' ', 1)
            tx.run(
                "MATCH (c:Customer {email: $email}), (o:Order {id: $order_id}) MERGE (c)-[:PLACED]->(o)",
                email=email,
                order_id=order_id
            )

        elif u_type == 'order' and v_type not in ['order', 'customer']:
            _, order_id = u.split(' ', 1)
            attr_type = v_type
            _, value = v.split(' ', 1)
            tx.run(
                "MATCH (o:Order {id: $order_id}), (a:Attribute {type: $type, value: $value}) MERGE (o)-[:HAS_ATTRIBUTE]->(a)",
                order_id=order_id,
                type=attr_type,
                value=value
            )

        elif u_type not in ['order', 'customer'] and v_type not in ['order', 'customer']:
            type1 = u_type
            _, value1 = u.split(' ', 1)
            type2 = v_type
            _, value2 = v.split(' ', 1)
            tx.run(
                "MATCH (a1:Attribute {type: $type1, value: $value1}), (a2:Attribute {type: $type2, value: $value2}) MERGE (a1)-[:CONNECTED_TO]->(a2)",
                type1=type1,
                value1=value1,
                type2=type2,
                value2=value2
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

