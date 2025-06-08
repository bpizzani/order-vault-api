from flask import g
from config.multi_tenant import TENANT_DATABASES
from neo4j import GraphDatabase

def load_tenant():
    user = get_logged_in_user()
    if not user:
        raise Exception("Unauthorized")

    tenant = TENANT_DATABASES.get(user.client_id)
    if not tenant:
        raise Exception("Unknown tenant")

    g.user = user
    g.client_id = user.client_id
    g.db_uri = tenant["postgres"]
    g.neo4j = GraphDatabase.driver(
        tenant["neo4j"]["uri"],
        auth=(tenant["neo4j"]["user"], tenant["neo4j"]["password"])
    )
