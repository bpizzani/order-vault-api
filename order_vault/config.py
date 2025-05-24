import os

class BaseConfig:
    SECRET_KEY = os.getenv("SECRET_KEY", "super-secret-key")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Client‐app endpoint, can also be overridden in Heroku config
    CLIENT_APP_API_URL = os.getenv(
        "CLIENT_APP_API_URL",
        "https://order-vault-client-webapp-13ee822f0ba9.herokuapp.com/api/orders"
    )

    # Neo4j connection settings
    NEO4J_URI      = os.getenv("NEO4J_URI", "neo4j+s://f34af65f.databases.neo4j.io")
    NEO4J_USER     = os.getenv("NEO4J_USER", "neo4j")
    NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "changeme")


class DevConfig(BaseConfig):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = (
        os.getenv("DATABASE_URL")
        or "sqlite:///dev.db"
    )


class ProdConfig(BaseConfig):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")
