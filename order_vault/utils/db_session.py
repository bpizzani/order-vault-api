from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

_session_cache = {}

def get_db_session_for_client(db_uri):
    if db_uri not in _session_cache:
        engine = create_engine(db_uri)
        Session = sessionmaker(bind=engine)
        _session_cache[db_uri] = Session()
    return _session_cache[db_uri]
