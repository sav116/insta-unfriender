"""
Database initialization utility
"""
from src.db.models import init_db
from src.services.user_service import UserService
from loguru import logger

def initialize_database():
    """Initialize database and create admin user"""
    logger.info("Initializing database...")
    
    # Initialize database tables
    init_db()
    
    # Initialize admin user
    user_service = UserService()
    user_service.initialize_admin()
    
    logger.info("Database initialization complete")

if __name__ == "__main__":
    initialize_database() 