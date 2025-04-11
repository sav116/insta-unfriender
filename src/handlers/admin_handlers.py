from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from loguru import logger
from src.services.user_service import UserService
from src.services.tracking_service import TrackingService
from src.services.instagram_service import InstagramService
from src.services.scheduler_service import SchedulerService
from src.db.session import get_session, close_session
from src.db.models import User, TrackedAccount, Follower, Unfollower

# States for conversation
WAITING_FOR_USERNAME = 1
WAITING_FOR_PASSWORD = 2
WAITING_FOR_INTERVAL = 1

# Initialize services
user_service = UserService()
tracking_service = TrackingService()
instagram_service = InstagramService()

# Admin command handlers
async def set_tech_account_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /set_tech_account command - admin only"""
    chat_id = str(update.effective_chat.id)
    
    # Check if user is admin
    if not user_service.is_admin(chat_id):
        await update.message.reply_text(
            "❌ This command is only available to administrators."
        )
        return ConversationHandler.END
    
    # Ask for username
    await update.message.reply_text(
        "🔑 *Admin: Set Technical Account*\n\n"
        "Please enter the new Instagram username for the technical account:",
        parse_mode="Markdown"
    )
    
    return WAITING_FOR_USERNAME

async def tech_account_username_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for username input in setting tech account"""
    username = update.message.text.strip()
    
    # Store username in context
    context.user_data["tech_username"] = username
    
    # Ask for password
    await update.message.reply_text(
        f"Username: *{username}*\n\n"
        "Now please enter the password for this account:",
        parse_mode="Markdown"
    )
    
    return WAITING_FOR_PASSWORD

async def tech_account_password_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for password input in setting tech account"""
    password = update.message.text.strip()
    username = context.user_data.get("tech_username")
    
    # For security, delete the message containing the password
    await update.message.delete()
    
    # Send processing message
    processing_message = await update.message.reply_text(
        f"⏳ Testing credentials for {username}..."
    )
    
    # Test the credentials
    temp_client = InstagramService()
    login_success = temp_client.login(username, password)
    
    if login_success:
        # Save credentials to database
        user_service.update_settings("instagram_username", username)
        user_service.update_settings("instagram_password", password)
        
        # Update the processing message
        await processing_message.edit_text(
            "✅ Technical account updated successfully.\n\n"
            f"New account: *{username}*",
            parse_mode="Markdown"
        )
    else:
        # Update the processing message with error
        await processing_message.edit_text(
            "❌ Failed to login with the provided credentials.\n"
            "Please check the username and password and try again."
        )
    
    return ConversationHandler.END

async def set_check_interval_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /set_check_interval command - admin only"""
    chat_id = str(update.effective_chat.id)
    
    # Check if user is admin
    if not user_service.is_admin(chat_id):
        await update.message.reply_text(
            "❌ This command is only available to administrators."
        )
        return ConversationHandler.END
    
    # Get current interval
    current_interval = user_service.get_setting("check_interval", "60")
    
    # Ask for new interval
    await update.message.reply_text(
        "⏱ *Admin: Set Check Interval*\n\n"
        f"Current interval: *{current_interval} minutes*\n\n"
        "Please enter the new check interval in minutes (minimum 15):",
        parse_mode="Markdown"
    )
    
    return WAITING_FOR_INTERVAL

async def check_interval_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for interval input in setting check interval"""
    try:
        interval = int(update.message.text.strip())
        
        # Validate interval
        if interval < 15:
            await update.message.reply_text(
                "❌ The interval must be at least 15 minutes to avoid API limits."
            )
            return WAITING_FOR_INTERVAL
        
        # Update setting
        user_service.update_settings("check_interval", str(interval))
        
        # Update scheduler if provided
        scheduler = context.bot_data.get("scheduler")
        if scheduler and isinstance(scheduler, SchedulerService):
            scheduler.update_check_interval()
        
        await update.message.reply_text(
            f"✅ Check interval updated to *{interval} minutes*.\n\n"
            "Changes will take effect on the next scheduled check.",
            parse_mode="Markdown"
        )
        
        return ConversationHandler.END
    
    except ValueError:
        await update.message.reply_text(
            "❌ Please enter a valid number for the interval."
        )
        return WAITING_FOR_INTERVAL

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /stats command - admin only"""
    chat_id = str(update.effective_chat.id)
    
    # Check if user is admin
    if not user_service.is_admin(chat_id):
        await update.message.reply_text(
            "❌ This command is only available to administrators."
        )
        return
    
    # Get stats from database
    session = get_session()
    
    try:
        total_users = session.query(User).count()
        total_tracked_accounts = session.query(TrackedAccount).count()
        total_followers = session.query(Follower).count()
        total_unfollowers = session.query(Unfollower).count()
        
        # Get tech account details
        instagram_username = user_service.get_setting("instagram_username", "Not set")
        check_interval = user_service.get_setting("check_interval", "60")
        
        stats_message = (
            "📊 *Bot Statistics*\n\n"
            f"Total users: *{total_users}*\n"
            f"Tracked accounts: *{total_tracked_accounts}*\n"
            f"Total followers: *{total_followers}*\n"
            f"Total unfollowers: *{total_unfollowers}*\n\n"
            
            "🔧 *Settings*\n\n"
            f"Technical account: *{instagram_username}*\n"
            f"Check interval: *{check_interval} minutes*"
        )
        
        await update.message.reply_text(
            stats_message,
            parse_mode="Markdown"
        )
    
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        await update.message.reply_text(
            "❌ Error fetching statistics."
        )
    finally:
        close_session(session) 