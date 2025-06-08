from flask import g
from flask_sqlalchemy import SQLAlchemy
from neo4j import GraphDatabase
from config.multi_tenant import CLIENT_DATABASES

sql_db_cache = {}
neo4j_driver_cache = {}

def load_client_connections(client_id):
    if client_id not in CLIENT_DATABASES:
        raise ValueError("Unknown client")

    config = CLIENT_DATABASES[client_id]

    # SQLAlchemy (Postgres)
    if client_id not in sql_db_cache:
        db = SQLAlchemy()
        db.init_app(g.app)
        g.app.config["SQLALCHEMY_DATABASE_URI"] = config["postgres_uri"]
        sql_db_cache[client_id] = db

    # Neo4j
    if client_id not in neo4j_driver_cache:
        driver = GraphDatabase.driver(
            config["neo4j_uri"],
            auth=(config["neo4j_user"], config["neo4j_password"])
        )
        neo4j_driver_cache[client_id] = driver

    # Attach to g
    g.db = sql_db_cache[client_id]
    g.neo4j = neo4j_driver_cache[client_id]
