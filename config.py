import os

class BaseConfig:
    SECRET_KEY = os.getenv("SECRET_KEY", "your_secret_key")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    CLIENT_APP_API_URL = os.getenv("CLIENT_APP_API_URL", "https://order-vault-client-webapp-13ee822f0ba9.herokuapp.com/api/orders")
    NEO4J_URI = os.getenv("NEO4J_URI","neo4j+s://f34af65f.databases.neo4j.io")
    NEO4J_USER = os.getenv("NEO4J_USER","neo4j")
    NEO4J_PASS = os.getenv("NEO4J_PASS","OPESlEPx3V4kYLSOo86X5fHX0k_HhKprCVG_erEfi7A")

class DevConfig(BaseConfig):
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL","postgresql://u32cgla1pp9fm7:p6f656fa0f2edb9dda1653485f118f3b8379d957dce3469ef41d13f34d73e8cb1@c5flugvup2318r.cluster-czrs8kj4isg7.us-east-1.rds.amazonaws.com:5432/dc0evnfhnut69e") or "sqlite:///dev.db"

class ProdConfig(BaseConfig):
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL","postgresql://u32cgla1pp9fm7:p6f656fa0f2edb9dda1653485f118f3b8379d957dce3469ef41d13f34d73e8cb1@c5flugvup2318r.cluster-czrs8kj4isg7.us-east-1.rds.amazonaws.com:5432/dc0evnfhnut69e")
