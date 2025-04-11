from loguru import logger
from src.db.session import get_session, close_session
from src.db.models import User, Settings
import os

class UserService:
    def __init__(self):
        # Initialize the admin user on startup
        self.initialize_admin()
    
    def initialize_admin(self):
        """Initialize the admin user based on ADMIN_CHAT_ID environment variable"""
        admin_chat_id = os.getenv("ADMIN_CHAT_ID")
        if not admin_chat_id:
            logger.warning("ADMIN_CHAT_ID not set in environment variables")
            return
        
        session = get_session()
        try:
            # Check if admin user exists
            admin = session.query(User).filter_by(chat_id=admin_chat_id).first()
            
            if not admin:
                # Create admin user
                admin = User(
                    chat_id=admin_chat_id,
                    username="admin",
                    is_admin=True
                )
                session.add(admin)
                
                # Initialize default settings
                instagram_username = os.getenv("INSTAGRAM_USERNAME")
                instagram_password = os.getenv("INSTAGRAM_PASSWORD")
                check_interval = os.getenv("CHECK_INTERVAL_MINUTES", "60")
                
                if instagram_username:
                    session.add(Settings(key="instagram_username", value=instagram_username))
                
                if instagram_password:
                    session.add(Settings(key="instagram_password", value=instagram_password))
                
                session.add(Settings(key="check_interval", value=check_interval))
                
                session.commit()
                logger.info(f"Admin user created with chat_id: {admin_chat_id}")
            else:
                # Ensure admin has admin rights
                if not admin.is_admin:
                    admin.is_admin = True
                    session.commit()
                    logger.info(f"Updated admin status for user with chat_id: {admin_chat_id}")
        
        except Exception as e:
            logger.error(f"Error initializing admin: {e}")
            session.rollback()
        finally:
            close_session(session)
    
    def get_or_create_user(self, chat_id, username=None):
        """Get an existing user or create a new one"""
        session = get_session()
        
        try:
            user = session.query(User).filter_by(chat_id=chat_id).first()
            
            if not user:
                user = User(
                    chat_id=chat_id,
                    username=username,
                    is_admin=False
                )
                session.add(user)
                session.commit()
                logger.info(f"New user created: {chat_id}")
            
            return user
        except Exception as e:
            logger.error(f"Error getting or creating user: {e}")
            session.rollback()
            return None
        finally:
            close_session(session)
    
    def is_admin(self, chat_id):
        """Check if a user is an admin"""
        session = get_session()
        
        try:
            user = session.query(User).filter_by(chat_id=chat_id).first()
            return user and user.is_admin
        except Exception as e:
            logger.error(f"Error checking admin status: {e}")
            return False
        finally:
            close_session(session)
    
    def update_settings(self, key, value):
        """Update a setting in the database"""
        session = get_session()
        
        try:
            setting = session.query(Settings).filter_by(key=key).first()
            
            if setting:
                setting.value = value
            else:
                setting = Settings(key=key, value=value)
                session.add(setting)
            
            session.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating setting: {e}")
            session.rollback()
            return False
        finally:
            close_session(session)
    
    def get_setting(self, key, default=None):
        """Get a setting from the database"""
        session = get_session()
        
        try:
            setting = session.query(Settings).filter_by(key=key).first()
            
            if setting:
                return setting.value
            return default
        except Exception as e:
            logger.error(f"Error getting setting: {e}")
            return default
        finally:
            close_session(session) 