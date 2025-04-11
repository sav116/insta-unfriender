import schedule
import time
import threading
from loguru import logger
from src.services.tracking_service import TrackingService
from src.services.user_service import UserService

class SchedulerService:
    def __init__(self, bot, job_callback):
        self.bot = bot
        self.job_callback = job_callback  # Callback to handle unfollower notifications
        self.tracking_service = TrackingService()
        self.user_service = UserService()
        self.thread = None
        self.running = False
        
        # Set the initial check interval
        self.update_check_interval()
    
    def update_check_interval(self):
        """Update the check interval from settings"""
        try:
            # Clear all existing jobs
            schedule.clear()
            
            # Get the check interval from settings
            interval_minutes = int(self.user_service.get_setting("check_interval", "60"))
            
            # Schedule the job with the new interval
            schedule.every(interval_minutes).minutes.do(self.run_check)
            logger.info(f"Scheduled follower checks every {interval_minutes} minutes")
            
            return True
        except Exception as e:
            logger.error(f"Error updating check interval: {e}")
            return False
    
    def run_check(self):
        """Run a check for all tracked accounts"""
        try:
            logger.info("Running scheduled follower check")
            results = self.tracking_service.check_all_accounts()
            
            if results:
                for result in results:
                    # Call the job callback to handle notifications
                    self.job_callback(result)
                
                logger.info(f"Found unfollowers for {len(results)} accounts")
            else:
                logger.info("No unfollowers found in this check")
                
            return True
        except Exception as e:
            logger.error(f"Error running scheduled check: {e}")
            return False
    
    def start(self):
        """Start the scheduler in a background thread"""
        if self.running:
            return False
        
        def run_scheduler():
            self.running = True
            logger.info("Scheduler started")
            
            while self.running:
                try:
                    schedule.run_pending()
                    time.sleep(1)
                except Exception as e:
                    logger.error(f"Error in scheduler loop: {e}")
        
        self.thread = threading.Thread(target=run_scheduler)
        self.thread.daemon = True
        self.thread.start()
        
        return True
    
    def stop(self):
        """Stop the scheduler"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=1)
            self.thread = None
        
        logger.info("Scheduler stopped")
        return True 