import os
from flask import Flask
from flask_cors import CORS

from config import DevConfig, ProdConfig
from extensions import db, migrate, cors as _cors, init_neo4j
from routes import register_blueprints


def create_app():
    """
    Application factory: creates and configures the Flask app.
    """
    # Select configuration class
    env = os.getenv("FLASK_ENV", "development").lower()
    config_class = ProdConfig if env == "production" else DevConfig

    # Create app, pointing to the correct folders
    app = Flask(
        __name__,
        instance_relative_config=True,
        template_folder="templates",
        static_folder="static"
    )
    app.config.from_object(config_class)

    # Initialize extensions
    _cors.init_app(app, supports_credentials=True)
    db.init_app(app)
    migrate.init_app(app, db)
    init_neo4j(app)

    # Register blueprints (all routes)
    register_blueprints(app)

    return app


# Create the app for running or importing
app = create_app()


if __name__ == "__main__":
    # In development, enable debug; in production, rely on Gunicorn/UWSGI
    debug_flag = app.config.get("DEBUG", False)
    port = int(os.getenv("PORT", 5000))

