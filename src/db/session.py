from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy import create_engine
import os
from dotenv import load_dotenv
from src.db.models import Base

load_dotenv()

database_url = os.getenv("DATABASE_URL", "sqlite:///bot_data.db")
engine = create_engine(database_url)

# Create tables if they don't exist
Base.metadata.create_all(engine)

# Create session factory
session_factory = sessionmaker(bind=engine)
Session = scoped_session(session_factory)

def get_session():
    """Get a database session"""
    return Session()

def close_session(session):
    """Close a database session"""
    session.close()
    Session.remove() 