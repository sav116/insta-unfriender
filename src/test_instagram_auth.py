#!/usr/bin/env python3
"""
Test script for Instagram authentication using simplified approach from FollowerBot.py example.
This script helps verify that the Instagram authentication is working properly.
"""

import os
import random
import time
from dotenv import load_dotenv
from instagrapi import Client
from instagrapi.exceptions import ChallengeRequired, SelectContactPointRecoveryForm
from loguru import logger
import sys

# Setup logger
logger.remove()
logger.add(sys.stderr, level="INFO")
logger.add("instagram_test.log", rotation="10 MB", level="DEBUG")

# Load environment variables
load_dotenv()

def handle_challenge(username, choice=None):
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

def challenge_code_handler(username, choice):
    """Custom challenge code handler"""
    logger.info(f"Challenge requested for {username} with choices: {choice}")
    # For testing, you can manually enter the code here
    # In production, you'd need to set up a proper way to get the code
    code = input(f"Enter code (6 digits) for {username} ({choice}): ")
    return code

def test_instagram_auth():
    """Test Instagram authentication using simplified approach"""
    # Get credentials from environment variables
    username = os.getenv("INSTAGRAM_USERNAME")
    password = os.getenv("INSTAGRAM_PASSWORD")
    
    if not username or not password:
        logger.error("Instagram credentials not found in environment variables")
        return False
    
    # Create client
    client = Client()
    logger.info(f"Attempting to authenticate as {username}")
    
    # Set up challenge handlers
    client.handle_challenge = handle_challenge
    client.challenge_code_handler = challenge_code_handler
    
    # Define session file path
    session_file = f"settings/{username}_session.json"
    os.makedirs("settings", exist_ok=True)
    
    # Try to load existing session
    if os.path.exists(session_file):
        try:
            logger.info(f"Attempting to load session for {username}")
            client.load_settings(session_file)
            
            # Test if session is valid
            try:
                me = client.account_info()
                logger.info(f"Successfully loaded session for {username}")
                logger.info(f"Logged in as {me.username} ({me.full_name})")
                return True
            except Exception as e:
                logger.warning(f"Session invalid: {e}")
        except Exception as e:
            logger.warning(f"Failed to load session: {e}")
    
    # Attempt login with challenge handling
    try:
        logger.info(f"Attempting fresh login for {username}")
        time.sleep(random.randint(1, 3))  # Random delay
        
        try:
            # Standard login attempt
            logger.info("Trying standard login method")
            logged_in = client.login(username, password)
            
            if logged_in:
                # Save session data
                client.dump_settings(session_file)
                logger.info(f"Successfully logged in as {username}")
                
                # Test account info
                me = client.account_info()
                logger.info(f"Account details: {me.username} ({me.full_name})")
                
                # Try a simple API call
                followers_count = client.user_info(me.pk).follower_count
                logger.info(f"Found {followers_count} followers")
                
                return True
            else:
                logger.error("Login returned false")
                return False
        except (ChallengeRequired, SelectContactPointRecoveryForm) as e:
            logger.warning(f"Challenge required: {e}. Will attempt with verification code.")
            
            # Try with verification code flow
            try:
                # Create a new client to avoid issues
                client = Client()
                client.handle_challenge = handle_challenge
                client.challenge_code_handler = challenge_code_handler
                
                # Try login with verification
                logger.info("Attempting login with verification code")
                logged_in = client.login(username, password)
                
                if logged_in:
                    # Save session
                    client.dump_settings(session_file)
                    logger.info(f"Successfully logged in with verification")
                    
                    # Test account access
                    me = client.account_info()
                    logger.info(f"Account details: {me.username} ({me.full_name})")
                    
                    return True
                else:
                    logger.error("Failed to login with verification")
                    return False
            except Exception as inner_ex:
                logger.error(f"Verification login failed: {inner_ex}")
                return False
        except Exception as e:
            logger.error(f"Standard login failed: {e}")
            return False
            
    except Exception as e:
        logger.error(f"Failed to login to Instagram: {e}")
        return False

if __name__ == "__main__":
    logger.info("Starting Instagram authentication test")
    success = test_instagram_auth()
    
    if success:
        logger.info("✅ Instagram authentication test completed successfully")
    else:
        logger.error("❌ Instagram authentication test failed") 