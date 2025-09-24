from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
from threading import Lock

_engines = {}
_sessionmakers = {}
_lock = Lock()

def get_db_session_for_client(db_uri):
    global _engines, _sessionmakers
    with _lock:
        if db_uri not in _engines:
            _engines[db_uri] = create_engine(
                db_uri,
                poolclass=QueuePool,
                pool_size=5,          # tune to your dyno concurrency
                max_overflow=10,      # short bursts
                pool_pre_ping=True,   # drop dead conns
                pool_recycle=300,     # avoid stale
            )
            _sessionmakers[db_uri] = sessionmaker(bind=_engines[db_uri], expire_on_commit=False)
    return _sessionmakers[db_uri]()  # returns a pooled Session


def get_db_session_for_client_old(db_uri):
    engine = create_engine(db_uri)
    Session = sessionmaker(bind=engine)
    return Session()
