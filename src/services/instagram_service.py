import os
import json
from instagrapi import Client
from instagrapi.exceptions import LoginRequired
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
        
        # Set realistic mobile device to avoid detection
        self.simulate_mobile_device()
        
        # Try to login
        try:
            self.login(username, password)
        except Exception as e:
            logger.error(f"Failed to initialize Instagram client: {e}")
    
    def simulate_mobile_device(self):
        """Configure client to simulate a realistic mobile device"""
        # Use a pre-defined set of device details
        device_settings = {
            "app_version": "203.0.0.29.118",
            "android_version": "29",
            "android_release": "10.0",
            "dpi": "640dpi",
            "resolution": "1440x3040",
            "manufacturer": "samsung",
            "device": "SM-G973F",
            "model": "beyond1",
            "cpu": "exynos9820",
            "version_code": "314665256"
        }
        
        # Set a realistic user agent
        user_agent = "Instagram 200.0.0.28.120 Android (29/10; 640dpi; 1440x3040; samsung; SM-G973F; beyond1; exynos9820; en_US; 314665256)"
        
        # Configure the client
        self.client.set_device(device_settings)
        self.client.set_user_agent(user_agent)
        
        # Set additional client settings
        self.client.set_settings({
            "uuids": {
                "phone_id": self._generate_uuid(),
                "uuid": self._generate_uuid(),
                "client_session_id": self._generate_uuid(),
                "advertising_id": self._generate_uuid(),
                "device_id": self._generate_android_device_id()
            }
        })
    
    def _generate_uuid(self):
        """Generate a random UUID"""
        return ''.join([random.choice('0123456789abcdef') for _ in range(32)])
    
    def _generate_android_device_id(self):
        """Generate a random Android device ID"""
        return 'android-' + ''.join([random.choice('0123456789abcdef') for _ in range(16)])
    
    def login(self, username, password):
        """Login to Instagram with the given credentials"""
        try:
            # Set client logger
            self.client.logger = logger
            
            # Define session file paths
            session_file = f"settings/{username}_session.json"
            cookies_file = f"settings/{username}_cookies.json"
            
            # Try to load existing session
            if os.path.exists(session_file) and os.path.exists(cookies_file):
                try:
                    logger.info(f"Attempting to load session for {username}")
                    self.client.load_settings(session_file)
                    
                    # Also try to load cookies separately if available
                    with open(cookies_file, 'r') as f:
                        cookies = json.load(f)
                        self.client.private.cookies.update(cookies)
                    
                    # Test if session is valid by making a simple API call
                    try:
                        me = self.client.account_info()
                        logger.info(f"Successfully loaded session for {username}")
                        return True
                    except Exception as e:
                        logger.warning(f"Session invalid: {e}")
                except Exception as e:
                    logger.warning(f"Failed to load session: {e}")
            
            # Define a simple challenge handler that accepts any verification code
            # but returns false to avoid triggering the verification flow
            def challenge_code_handler(username, choice):
                logger.info(f"Challenge requested with choices: {choice}")
                return False  # Skip verification
            
            # Apply the challenge handler
            self.client.challenge_code_handler = challenge_code_handler
            
            # Try to login using BASIC flow (without web cookies)
            try:
                logger.info(f"Attempting login with basic flow for {username}")
                logged_in = self.client.login(username, password)
                
                if logged_in:
                    # Save session data
                    self.client.dump_settings(session_file)
                    
                    # Also save cookies separately for better persistence
                    with open(cookies_file, 'w') as f:
                        json.dump(self.client.private.cookies.get_dict(), f)
                    
                    logger.info(f"Successfully logged in as {username}")
                    return True
                else:
                    logger.error(f"Basic login returned false for {username}")
            except Exception as e:
                # If login fails with challenge, try setting a random verification code
                # which sometimes helps bypass the protection
                logger.warning(f"Basic login failed: {e}. Trying alternative method...")
                try:
                    # Create a completely new client instance to avoid conflicts
                    self.client = Client()
                    self.simulate_mobile_device()
                    
                    # Try the web-login flow instead
                    logged_in = self.client.login(username, password, verification_code="123456")
                    
                    if logged_in:
                        # Save session data
                        self.client.dump_settings(session_file)
                        
                        # Also save cookies separately
                        with open(cookies_file, 'w') as f:
                            json.dump(self.client.private.cookies.get_dict(), f)
                        
                        logger.info(f"Successfully logged in with alternative method")
                        return True
                    else:
                        logger.error("Alternative login method also failed")
                except Exception as alt_error:
                    logger.error(f"Alternative login failed: {alt_error}")
            
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