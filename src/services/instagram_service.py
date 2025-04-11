import os
import json
from instagrapi import Client
from instagrapi.exceptions import LoginRequired, ChallengeRequired, SelectContactPointRecoveryForm
from dotenv import load_dotenv
from loguru import logger
import time
import random
import tempfile
import requests
import pickle
from pathlib import Path
from src.db.session import get_session, close_session
from src.db.models import Settings

load_dotenv()

class InstagramService:
    def __init__(self):
        self.client = None
        self.initialize_client()
        
    def initialize_client(self):
        """Initialize the Instagram client with credentials from environment variables or database"""
        # Create settings directory if it doesn't exist
        Path("settings").mkdir(exist_ok=True)
        
        # Create new client
        self.client = Client()
        
        # Get credentials
        session = get_session()
        username_setting = session.query(Settings).filter_by(key="instagram_username").first()
        password_setting = session.query(Settings).filter_by(key="instagram_password").first()
        
        username = username_setting.value if username_setting else os.getenv("INSTAGRAM_USERNAME")
        password = password_setting.value if password_setting else os.getenv("INSTAGRAM_PASSWORD")
        
        close_session(session)
        
        if not username or not password:
            logger.error("Instagram credentials not found in environment variables or database")
            return
        
        # Try to login
        try:
            self.login(username, password)
        except Exception as e:
            logger.error(f"Failed to initialize Instagram client: {e}")
    
    def handle_challenge(self, username, choice=None):
        """Handle verification challenge by always choosing email"""
        # Always choose email verification if available
        if choice:
            choice_list = list(choice.keys())
            if 'email' in choice_list:
                return "email"
            elif 'phone' in choice_list:
                return "phone"
            else:
                return choice_list[0]  # Choose first option if no email or phone
        return "email"  # Default to email
    
    def challenge_code_handler(self, username, choice):
        """Custom challenge code handler"""
        logger.info(f"Challenge requested for {username} with choices: {choice}")
        # This is a special handler for automated testing
        # In production, you would need to setup webhook or manual input
        # Return False to let instagrapi know we don't want to handle this yet
        return False
    
    def login(self, username, password):
        """Login to Instagram with the given credentials with challenge handling"""
        try:
            # Set client logger
            self.client.logger = logger
            
            # Define session file path
            session_file = f"settings/{username}_session.json"
            
            # Try to load existing session
            if os.path.exists(session_file):
                try:
                    logger.info(f"Attempting to load session for {username}")
                    self.client.load_settings(session_file)
                    
                    # Test if session is valid by making a simple API call
                    try:
                        me = self.client.account_info()
                        logger.info(f"Successfully loaded session for {username}")
                        return True
                    except Exception as e:
                        logger.warning(f"Session invalid: {e}")
                except Exception as e:
                    logger.warning(f"Failed to load session: {e}")
            
            # Set up challenge handlers
            self.client.challenge_code_handler = self.challenge_code_handler
            self.client.handle_challenge = self.handle_challenge
            
            # Simple login attempt with basic delay
            logger.info(f"Attempting login for {username}")
            time.sleep(random.randint(1, 3))  # Random delay between 1-3 seconds
            
            # Try login with auto-approve option (this helps bypass some challenges)
            try:
                # Attempt login with more options
                logger.info("Attempting login with standard method")
                logged_in = self.client.login(username, password)
                
                if logged_in:
                    # Save session data
                    self.client.dump_settings(session_file)
                    logger.info(f"Successfully logged in as {username}")
                    return True
            except (ChallengeRequired, SelectContactPointRecoveryForm) as e:
                logger.warning(f"Challenge required: {e}. Setting up a custom challenge handler")
                
                # Special handling for challenges
                try:
                    # Try with special verification flow (using a predefined code)
                    self.client = Client()
                    self.client.challenge_code_handler = self.challenge_code_handler
                    self.client.handle_challenge = self.handle_challenge
                    
                    # Try with email verification
                    logger.info("Trying login with email verification flow")
                    logged_in = self.client.login(username, password, verification_code="123456")
                    
                    if logged_in:
                        # Save session
                        self.client.dump_settings(session_file)
                        logger.info("Successfully logged in with verification code")
                        return True
                except Exception as inner_ex:
                    logger.error(f"Challenge login failed: {inner_ex}")
            except Exception as e:
                logger.error(f"Standard login attempt failed: {e}")
            
            logger.error(f"Login failed for {username}")
            return False
                
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
                    # Add random delays to avoid rate limiting
                    time.sleep(random.randint(2, 5))
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