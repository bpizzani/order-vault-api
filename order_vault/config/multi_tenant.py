
CLIENT_DATABASES = {
    "client_a": {
        "postgres_uri": "postgresql://u32cgla1pp9fm7:p6f656fa0f2edb9dda1653485f118f3b8379d957dce3469ef41d13f34d73e8cb1@c5flugvup2318r.cluster-czrs8kj4isg7.us-east-1.rds.amazonaws.com:5432/dc0evnfhnut69e",
        "neo4j_uri": "neo4j+s://f34af65f.databases.neo4j.io",
        "neo4j_user": "neo4j",
        "neo4j_password": "OPESlEPx3V4kYLSOo86X5fHX0k_HhKprCVG_erEfi7A"
    },
    "client_b": {
        "postgres_uri": "postgresql://user:pass@host:port/db_client_b",
        "neo4j_uri": "neo4j+s://host_b.neo4j.io",
        "neo4j_user": "neo4j",
        "neo4j_password": "password_b"
    },
}
app.config["SQLALCHEMY_DATABASE_URI"] = 'postgresql://u32cgla1pp9fm7:p6f656fa0f2edb9dda1653485f118f3b8379d957dce3469ef41d13f34d73e8cb1@c5flugvup2318r.cluster-czrs8kj4isg7.us-east-1.rds.amazonaws.com:5432/dc0evnfhnut69e' #os.getenv('DATABASE_URL') #os.environ.get("DATABASE_URL") #"sqlite:///orders_v4.db" #os.environ.get("DATABASE_URL", "sqlite:///orders_v4.db")
