from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

def get_db_session_for_client(db_uri):
    engine = create_engine(db_uri)
    Session = sessionmaker(bind=engine)
    return Session()
