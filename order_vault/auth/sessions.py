from flask import session, g
from order_vault.models.user import User
from order_vault.models.client_subscription import ClientSubscription
from order_vault.models.tenant import Tenant
from order_vault.utils.crypto import enc, dec
from neo4j import GraphDatabase

def load_tenant_from_session():
    user_id = session.get("user_id")
    if not user_id:
        return Exception("Unauthorized – user not logged in")

    user = User.query.get(user_id)
    if not user:
        return

    tenant = Tenant.query.filter_by(client_id=user.client_id).first()
    if not tenant:
        return Exception("Unknown tenant configuration")
        
    #get subscription type
    subscription = ClientSubscription.query.filter_by(client_id=user.client_id).first()
    
    pg_uri_dec = dec(tenant.pg_uri_enc)
    neo4j_uri_dec = dec(tenant.neo4j_uri_enc)
    neo4j_user_dec = dec(tenant.neo4j_user_enc)
    neo4j_pass_dec = dec(tenant.neo4j_pass_enc)
    
    print("Tenant Found")

    g.user = user
    g.subscription_type = subscription.type
    g.client_id = user.client_id
    g.client_email = user.email
    print(g.client_id)
    print(tenant)
    g.db_uri = pg_uri_dec
    g.neo4j_driver = GraphDatabase.driver(
        neo4j_uri_dec,
        auth=(neo4j_user_dec, neo4j_pass_dec)
    )
    
    print(g.neo4j_driver)
