import os
from instagrapi import Client
from instagrapi.exceptions import LoginRequired
from dotenv import load_dotenv
from loguru import logger
import time
from src.db.session import get_session, close_session
from src.db.models import Settings

load_dotenv()

class InstagramService:
    def __init__(self):
        self.client = None
        self.initialize_client()
        
    def initialize_client(self):
        """Initialize the Instagram client with credentials from environment variables or database"""
        self.client = Client()
        try:
            # Try to get credentials from database first (for admin-updated credentials)
            session = get_session()
            username_setting = session.query(Settings).filter_by(key="instagram_username").first()
            password_setting = session.query(Settings).filter_by(key="instagram_password").first()
            
            username = username_setting.value if username_setting else os.getenv("INSTAGRAM_USERNAME")
            password = password_setting.value if password_setting else os.getenv("INSTAGRAM_PASSWORD")
            
            close_session(session)
            
            if not username or not password:
                logger.error("Instagram credentials not found in environment variables or database")
                return
                
            self.login(username, password)
        except Exception as e:
            logger.error(f"Failed to initialize Instagram client: {e}")
    
    def login(self, username, password):
        """Login to Instagram with the given credentials"""
        try:
            self.client.login(username, password)
            logger.info(f"Successfully logged in as {username}")
            return True
        except Exception as e:
            logger.error(f"Failed to login to Instagram: {e}")
            return False
    
    def get_user_id_by_username(self, username):
        """Get user ID by username"""
        try:
            user_info = self.client.user_info_by_username(username)
            return user_info.pk
        except Exception as e:
            logger.error(f"Failed to get user ID by username {username}: {e}")
            return None
    
    def is_private_account(self, username):
        """Check if an account is private"""
        try:
            user_info = self.client.user_info_by_username(username)
            return user_info.is_private
        except Exception as e:
            logger.error(f"Failed to check if account {username} is private: {e}")
            return None
    
    def send_follow_request(self, username):
        """Send a follow request to a private account"""
        try:
            user_id = self.get_user_id_by_username(username)
            if not user_id:
                return False
            
            result = self.client.user_follow(user_id)
            return result
        except Exception as e:
            logger.error(f"Failed to send follow request to {username}: {e}")
            return False
    
    def get_followers(self, user_id=None, username=None):
        """Get a list of followers for the specified user"""
        try:
            if not user_id and username:
                user_id = self.get_user_id_by_username(username)
            
            if not user_id:
                logger.error("No user ID or username provided to get followers")
                return []
            
            # Get all followers with pagination
            all_followers = []
            max_retries = 3
            retries = 0
            
            while retries < max_retries:
                try:
                    all_followers = self.client.user_followers(user_id, amount=0)  # 0 means all followers
                    break
                except LoginRequired:
                    logger.warning("Login required, attempting to reinitialize client")
                    self.initialize_client()
                    retries += 1
                except Exception as e:
                    # Check if it's a private account error
                    if "Private account" in str(e):
                        logger.error(f"Cannot view followers of private account {user_id}")
                        return []
                    
                    logger.error(f"Error fetching followers for {user_id}: {e}")
                    retries += 1
                    time.sleep(5)  # Wait before retry
            
            return [
                {
                    "instagram_user_id": follower_id,
                    "username": follower_info.username,
                    "full_name": follower_info.full_name
                }
                for follower_id, follower_info in all_followers.items()
            ]
        except Exception as e:
            logger.error(f"Failed to get followers: {e}")
            return []
    
    def get_user_info(self, user_id):
        """Get information about a specific user"""
        try:
            user_info = self.client.user_info(user_id)
            return {
                "instagram_user_id": user_id,
                "username": user_info.username,
                "full_name": user_info.full_name,
                "is_private": user_info.is_private
            }
        except Exception as e:
            logger.error(f"Failed to get user info for {user_id}: {e}")
            return None 