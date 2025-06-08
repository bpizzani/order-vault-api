from flask import request, g
from utils.db_router import load_client_connections

def with_client_context(view_func):
    def wrapper(*args, **kwargs):
        # Get client ID from header, token, or session
        client_id = request.headers.get("X-Client-ID")  # or use auth token
        if not client_id:
            return {"error": "Missing client ID"}, 400

        try:
            g.app = request.environ.get("flask.app")  # attach app instance to g
            load_client_connections(client_id)
        except Exception as e:
            return {"error": str(e)}, 500

        return view_func(*args, **kwargs)

    wrapper.__name__ = view_func.__name__
    return wrapper
