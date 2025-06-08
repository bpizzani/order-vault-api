from flask import g, session
from config.multi_tenant import TENANT_DATABASES
from neo4j import GraphDatabase

def load_tenant():
    user = get_logged_in_user()  # implement based on your auth/session
    if not user:
        raise Exception("Unauthorized")

    client_id = user.client_id
    tenant = TENANT_DATABASES.get(client_id)
    if not tenant:
        raise Exception("Unknown tenant")

    g.client_id = client_id
    g.db_uri = tenant["postgres"]
    g.neo4j = GraphDatabase.driver(
        tenant["neo4j"]["uri"],
        auth=(tenant["neo4j"]["user"], tenant["neo4j"]["password"])
    )
