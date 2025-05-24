#from flask import Flask
#from flask_cors import CORS

#app = Flask(__name__)
#CORS(app)  # This allows all domains to access your API

#from order_vault import main

from flask import Flask
from .extensions import db, migrate, cors, init_neo4j
from .routes import register_blueprints

def create_app(config_object="config.DevConfig"):
    app = Flask(__name__, static_folder="../static", template_folder="../templates")
    app.config.from_object(config_object)

    # initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    cors.init_app(app, supports_credentials=True)
    init_neo4j(app)

    # register all route blueprints
    register_blueprints(app)

    return app
