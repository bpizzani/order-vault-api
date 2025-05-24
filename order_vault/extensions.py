from flask_sqlalchemy import SQLAlchemy
from flask_migrate    import Migrate
from flask_cors       import CORS
from neo4j            import GraphDatabase

db      = SQLAlchemy()
migrate = Migrate()
cors    = CORS()

def init_neo4j(app):
    """Attach a Neo4j driver to app.neo4j_driver."""
    uri  = app.config["NEO4J_URI"]
    user = app.config["NEO4J_USER"]
    pw   = app.config["NEO4J_PASSWORD"]
    app.neo4j_driver = GraphDatabase.driver(uri, auth=(user, pw))
