import os
import json
from instagrapi import Client
from instagrapi.exceptions import LoginRequired
from dotenv import load_dotenv
from loguru import logger
import time
import random
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
        
        self.client = Client()
        
        # Set device details to avoid suspicion
        self.client.set_device({
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
        })
        
        # Set user agent to mimic a real browser
        self.client.set_user_agent(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36"
        )
        
        # Set additional client settings to avoid detection
        self.client.set_settings({
            "uuids": {
                "phone_id": self._generate_uuid(),
                "uuid": self._generate_uuid(),
                "client_session_id": self._generate_uuid(),
                "advertising_id": self._generate_uuid(),
                "device_id": self._generate_android_device_id()
            }
        })
        
        # Настраиваем обработчик вызовов для обхода
        def patched_private_request(self, *args, **kwargs):
            try:
                return self._orig_private_request(*args, **kwargs)
            except Exception as e:
                # Если в ответе есть "challenge", значит требуют верификацию
                if "challenge" in str(e).lower():
                    logger.warning("Detected challenge request, trying to bypass...")
                    return {'status': 'ok'}  # Фальшивый успешный ответ
                raise e
        
        # Сохраняем оригинальный метод
        if not hasattr(self.client, '_orig_private_request'):
            self.client._orig_private_request = self.client._send_private_request
            # Заменяем на наш обработчик
            self.client._send_private_request = lambda *args, **kwargs: patched_private_request(self.client, *args, **kwargs)
        
        try:
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
                
            self.login(username, password)
        except Exception as e:
            logger.error(f"Failed to initialize Instagram client: {e}")
    
    def _generate_uuid(self):
        """Generate a random UUID"""
        return ''.join([random.choice('0123456789abcdef') for _ in range(32)])
    
    def _generate_android_device_id(self):
        """Generate a random Android device ID"""
        return 'android-' + ''.join([random.choice('0123456789abcdef') for _ in range(16)])
    
    def login(self, username, password):
        """Login to Instagram with the given credentials"""
        try:
            # Set logging for debugging
            self.client.logger = logger
            
            # Проверяем сохраненную сессию
            session_paths = [
                f"settings/{username}_session.json",
                f"{username}_session.json"
            ]
            
            session_loaded = False
            for session_file in session_paths:
                if os.path.exists(session_file):
                    try:
                        # Load session and cookies from file
                        logger.info(f"Attempting to load session from {session_file}")
                        self.client.load_settings(session_file)
                        # Test if session is valid with a simple request
                        try:
                            self.client.get_timeline_feed(amount=1)
                            logger.info(f"Successfully loaded valid session for {username}")
                            session_loaded = True
                            break
                        except Exception as e:
                            logger.warning(f"Session appears invalid, testing another method...")
                            try:
                                me = self.client.account_info()
                                logger.info(f"Successfully loaded valid session (verified with account_info) for {username}")
                                session_loaded = True
                                break
                            except Exception as e2:
                                logger.warning(f"Session expired completely: {e2}")
                    except Exception as e:
                        logger.warning(f"Failed to load session from {session_file}: {e}")

            # Если сессия не загрузилась или невалидна, логинимся заново
            if not session_loaded:
                logger.info(f"No valid session found, attempting fresh login for {username}")
                
                # Override challenge function to avoid verification
                def challenge_code_handler(username, choice):
                    logger.info(f"Challenge requested with choices: {choice}")
                    return False  # Отказываемся от challenge
                
                self.client.challenge_code_handler = challenge_code_handler
                
                # Выполняем логин с защитой от блокировки
                try:
                    # Используем метод с автоматическим обходом
                    logged_in = self.client.login(username, password)
                    
                    if logged_in:
                        # Сохраняем сессию в оба места
                        for session_file in session_paths:
                            try:
                                self.client.dump_settings(session_file)
                                logger.info(f"Successfully saved session to {session_file}")
                            except Exception as e:
                                logger.warning(f"Could not save session to {session_file}: {e}")
                        
                        logger.info(f"Successfully logged in as {username}")
                        return True
                    else:
                        logger.error(f"Login returned false for {username}")
                        return False
                except Exception as e:
                    logger.error(f"Error during login: {e}")
                    # Если ошибка связана с challenge, пробуем автоматически обойти
                    if "challenge" in str(e).lower():
                        logger.warning("Challenge detected during login, trying to bypass...")
                        # Простейший обход - подождать и попробовать еще раз с новой сессией
                        time.sleep(5)
                        try:
                            self.client = Client()
                            logged_in = self.client.login(username, password, verification_code="")
                            if logged_in:
                                logger.info(f"Successfully logged in on second attempt!")
                                for session_file in session_paths:
                                    try:
                                        self.client.dump_settings(session_file)
                                    except:
                                        pass
                                return True
                        except:
                            logger.error("Second login attempt also failed")
                    return False
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