import datetime
from loguru import logger
from src.db.session import get_session, close_session
from src.db.models import TrackedAccount, Follower, Unfollower
from src.services.instagram_service import InstagramService

class TrackingService:
    def __init__(self):
        self.instagram_service = InstagramService()
    
    def start_tracking(self, user_id, instagram_username):
        """Start tracking an Instagram account's followers"""
        session = get_session()
        
        try:
            # Check if the account exists
            logger.info(f"Attempting to find user ID for {instagram_username}")
            instagram_user_id = self.instagram_service.get_user_id_by_username(instagram_username)
            if not instagram_user_id:
                close_session(session)
                return False, "Account not found or Instagram API error"
            
            logger.info(f"Successfully found user ID {instagram_user_id} for {instagram_username}")
            
            # Check if already tracking
            existing = session.query(TrackedAccount).filter_by(
                user_id=user_id, 
                instagram_username=instagram_username
            ).first()
            
            if existing:
                close_session(session)
                return False, "You are already tracking this account"
            
            # Check if the account is private
            logger.info(f"Checking if {instagram_username} is private")
            is_private = self.instagram_service.is_private_account(instagram_username)
            logger.info(f"Account {instagram_username} is {'private' if is_private else 'public'}")
            
            # Create a new tracked account
            tracked_account = TrackedAccount(
                user_id=user_id,
                instagram_username=instagram_username,
                instagram_user_id=instagram_user_id,
                is_private=is_private,
                follow_requested=False,
                last_check=datetime.datetime.utcnow()
            )
            
            session.add(tracked_account)
            session.commit()
            
            # If the account is public, save the initial followers
            if not is_private:
                logger.info(f"Account {instagram_username} is public, fetching followers")
                self.update_followers(tracked_account.id)
                return True, "Started tracking followers successfully"
            else:
                # For private accounts, send a follow request
                logger.info(f"Sending follow request to private account {instagram_username}")
                success = self.instagram_service.send_follow_request(instagram_username)
                
                if success:
                    tracked_account.follow_requested = True
                    session.commit()
                    logger.info(f"Follow request sent to {instagram_username}")
                    return True, "Account is private. Follow request sent. Please accept it and confirm in the bot."
                else:
                    logger.error(f"Failed to send follow request to {instagram_username}")
                    # Still track the account but warn about follow request
                    return True, "Account is private. We couldn't send a follow request automatically. Please follow this account manually and confirm in the bot."
                
        except Exception as e:
            logger.error(f"Error starting tracking: {e}")
            session.rollback()
            return False, f"Error: {str(e)}"
        finally:
            close_session(session)
    
    def confirm_follow_accepted(self, tracked_account_id):
        """Confirm that a follow request has been accepted and save initial followers"""
        session = get_session()
        
        try:
            tracked_account = session.query(TrackedAccount).filter_by(id=tracked_account_id).first()
            if not tracked_account:
                close_session(session)
                return False, "Tracked account not found"
            
            # Update followers
            result = self.update_followers(tracked_account_id)
            if result:
                tracked_account.follow_requested = False
                session.commit()
                return True, "Follow confirmed and initial followers saved"
            else:
                return False, "Failed to save followers. Please try again or check if the follow request was accepted."
                
        except Exception as e:
            logger.error(f"Error confirming follow: {e}")
            session.rollback()
            return False, f"Error: {str(e)}"
        finally:
            close_session(session)
    
    def update_followers(self, tracked_account_id):
        """Update the followers for a tracked account"""
        session = get_session()
        
        try:
            tracked_account = session.query(TrackedAccount).filter_by(id=tracked_account_id).first()
            if not tracked_account:
                close_session(session)
                return False
            
            # Get current followers
            followers = self.instagram_service.get_followers(user_id=tracked_account.instagram_user_id)
            if not followers:
                close_session(session)
                return False
            
            # Get existing followers from database
            existing_followers = session.query(Follower).filter_by(tracked_account_id=tracked_account_id).all()
            existing_follower_ids = {f.instagram_user_id for f in existing_followers}
            
            # Identify new and current followers
            current_follower_ids = {f["instagram_user_id"] for f in followers}
            
            # Identify unfollowers (followers that exist in database but not in current followers)
            unfollower_ids = existing_follower_ids - current_follower_ids
            
            # Add new followers to database
            for follower_data in followers:
                if follower_data["instagram_user_id"] not in existing_follower_ids:
                    new_follower = Follower(
                        instagram_user_id=follower_data["instagram_user_id"],
                        username=follower_data["username"],
                        full_name=follower_data["full_name"],
                        tracked_account_id=tracked_account_id
                    )
                    session.add(new_follower)
            
            # Process unfollowers
            unfollowers_data = []
            for unfollower_id in unfollower_ids:
                # Get the follower object
                follower = next((f for f in existing_followers if f.instagram_user_id == unfollower_id), None)
                
                if follower:
                    # Create unfollower record
                    unfollower = Unfollower(
                        instagram_user_id=follower.instagram_user_id,
                        username=follower.username,
                        full_name=follower.full_name,
                        tracked_account_id=tracked_account_id
                    )
                    session.add(unfollower)
                    
                    # Add to return data
                    unfollowers_data.append({
                        "username": follower.username,
                        "full_name": follower.full_name
                    })
                    
                    # Delete the follower record
                    session.delete(follower)
            
            # Update the last_check timestamp
            tracked_account.last_check = datetime.datetime.utcnow()
            
            session.commit()
            return unfollowers_data
            
        except Exception as e:
            logger.error(f"Error updating followers: {e}")
            session.rollback()
            return False
        finally:
            close_session(session)
    
    def check_all_accounts(self):
        """Check all tracked accounts for unfollowers"""
        session = get_session()
        results = []
        
        try:
            tracked_accounts = session.query(TrackedAccount).all()
            
            for account in tracked_accounts:
                # Skip accounts with pending follow requests
                if account.follow_requested:
                    continue
                
                # Check for unfollowers
                unfollowers = self.update_followers(account.id)
                
                if unfollowers and len(unfollowers) > 0:
                    results.append({
                        "user_id": account.user_id,
                        "instagram_username": account.instagram_username,
                        "unfollowers": unfollowers
                    })
            
            return results
            
        except Exception as e:
            logger.error(f"Error checking accounts: {e}")
            return []
        finally:
            close_session(session)
    
    def get_tracked_accounts(self, user_id):
        """Get all tracked accounts for a user"""
        session = get_session()
        
        try:
            accounts = session.query(TrackedAccount).filter_by(user_id=user_id).all()
            return accounts
        except Exception as e:
            logger.error(f"Error getting tracked accounts: {e}")
            return []
        finally:
            close_session(session)
    
    def stop_tracking(self, user_id, tracked_account_id):
        """Stop tracking an Instagram account"""
        session = get_session()
        
        try:
            tracked_account = session.query(TrackedAccount).filter_by(
                id=tracked_account_id, 
                user_id=user_id
            ).first()
            
            if not tracked_account:
                close_session(session)
                return False, "Tracked account not found"
            
            session.delete(tracked_account)
            session.commit()
            
            return True, f"Stopped tracking {tracked_account.instagram_username}"
            
        except Exception as e:
            logger.error(f"Error stopping tracking: {e}")
            session.rollback()
            return False, f"Error: {str(e)}"
        finally:
            close_session(session) 