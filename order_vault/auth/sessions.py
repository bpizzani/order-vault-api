from flask import session, g
from order_vault.models.user import User
from order_vault.models.client_subscription import ClientSubscription
from order_vault.settings.tenants import TENANT_DATABASES
from neo4j import GraphDatabase

def load_tenant_from_session():
    user_id = session.get("user_id")
    if not user_id:
        return Exception("Unauthorized – user not logged in")

    user = User.query.get(user_id)
    if not user:
        return

    tenant = TENANT_DATABASES.get(user.client_id)
    if not tenant:
        return Exception("Unknown tenant configuration")
        
    #get subscription type
    subscription = ClientSubscription.query.filter_by(client_id=user.client_id).first()
        
    print("Tenant Found")

    g.user = user
    g.subscription_type = subscription.type
    g.client_id = user.client_id
    g.client_email = user.email
    print(g.client_id)
    print(tenant)
    g.db_uri = tenant["postgres_uri"]
    g.neo4j_driver = GraphDatabase.driver(
        tenant["neo4j_uri"],
        auth=(tenant["neo4j_user"], tenant["neo4j_password"])
    )
    print(g.neo4j_driver)
