from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from neo4j import GraphDatabase

db = SQLAlchemy()
migrate = Migrate()
cors = CORS()

def init_neo4j(app):
    uri = app.config["NEO4J_URI"]
    auth = (app.config["NEO4J_USER"], app.config["NEO4J_PASS"])
    driver = GraphDatabase.driver(uri, auth=auth)
    # store on app for access in blueprints/services
    app.neo4j_driver = driver
