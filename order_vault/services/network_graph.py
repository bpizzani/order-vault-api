import networkx as nx


def build_graph_from_order(order_data: dict) -> nx.Graph:
    """
    Construct a NetworkX graph from a single order's data.

    Nodes:
      - Customer <email>
      - Order <id>
      - Attribute nodes for card_details, email, device_id, phone, ip, promocode

    Edges:
      - Customer -> Order
      - Order -> each Attribute

    Returns:
        A NetworkX Graph ready for Neo4j ingestion.
    """
    G = nx.Graph()

    # Create order node
    order_id = order_data.get('id')
    order_node = f"Order {order_id}"
    G.add_node(order_node, type='order')

    # Create customer node
    email = order_data.get('email', '').lower()
    customer_node = f"Customer {email}"
    G.add_node(customer_node, type='customer')

    # Link customer to order
    G.add_edge(customer_node, order_node)

    # Add attribute nodes and edges
    attributes = ['card_details', 'email', 'device_id', 'phone', 'ip', 'promocode']
    for attr in attributes:
        value = order_data.get(attr)
        if value:
            node_id = f"{attr} {value}"
            G.add_node(node_id, type=attr)
            G.add_edge(order_node, node_id)

    return G

