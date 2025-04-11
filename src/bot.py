import os
import sys
from dotenv import load_dotenv
from loguru import logger
from telegram import Update, BotCommand
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters
)

# Load handlers
from src.handlers.common_handlers import (
    start_command,
    help_command,
    unknown_command,
    error_handler,
    start_button_handler
)
from src.handlers.tracking_handlers import (
    track_command,
    track_username_input,
    handle_track_account_button,
    handle_list_accounts_button,
    handle_confirm_follow,
    handle_stop_tracking,
    accounts_command,
    notify_unfollowers,
    WAITING_FOR_USERNAME as TRACKING_WAITING_FOR_USERNAME
)
from src.handlers.admin_handlers import (
    set_tech_account_command,
    tech_account_username_input,
    tech_account_password_input,
    set_check_interval_command,
    check_interval_input,
    stats_command,
    WAITING_FOR_USERNAME as ADMIN_WAITING_FOR_USERNAME,
    WAITING_FOR_PASSWORD,
    WAITING_FOR_INTERVAL
)

# Load services
from src.services.scheduler_service import SchedulerService
from src.db.models import init_db

# Load environment variables
load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Configure logging
logger.remove()
logger.add(sys.stderr, level="INFO")
logger.add("logs/bot_{time}.log", rotation="1 day", retention="7 days", level="DEBUG")

async def setup_commands(application: Application):
    """Setup bot commands in menu"""
    commands = [
        BotCommand("start", "Start the bot"),
        BotCommand("help", "Show help message"),
        BotCommand("track", "Track a new Instagram account"),
        BotCommand("accounts", "List your tracked accounts")
    ]
    
    await application.bot.set_my_commands(commands)
    logger.info("Bot commands set up")

def create_application():
    """Create and configure the bot application"""
    # Initialize database
    init_db()
    
    # Create application
    application = Application.builder().token(TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("accounts", accounts_command))
    application.add_handler(CommandHandler("stats", stats_command))
    
    # Track command conversation handler
    track_conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("track", track_command),
            CallbackQueryHandler(handle_track_account_button, pattern="^track_account$")
        ],
        states={
            TRACKING_WAITING_FOR_USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, track_username_input)]
        },
        fallbacks=[CommandHandler("cancel", help_command)]
    )
    application.add_handler(track_conv_handler)
    
    # Admin command handlers
    tech_account_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("set_tech_account", set_tech_account_command)],
        states={
            ADMIN_WAITING_FOR_USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, tech_account_username_input)],
            WAITING_FOR_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, tech_account_password_input)]
        },
        fallbacks=[CommandHandler("cancel", help_command)]
    )
    application.add_handler(tech_account_conv_handler)
    
    interval_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("set_check_interval", set_check_interval_command)],
        states={
            WAITING_FOR_INTERVAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, check_interval_input)]
        },
        fallbacks=[CommandHandler("cancel", help_command)]
    )
    application.add_handler(interval_conv_handler)
    
    # Callback query handlers
    application.add_handler(CallbackQueryHandler(handle_list_accounts_button, pattern="^list_accounts$"))
    application.add_handler(CallbackQueryHandler(handle_confirm_follow, pattern="^confirm_follow:"))
    application.add_handler(CallbackQueryHandler(handle_stop_tracking, pattern="^stop_tracking:"))
    application.add_handler(CallbackQueryHandler(start_button_handler, pattern="^start$"))
    
    # Add error handler
    application.add_error_handler(error_handler)
    
    # Add fallback for unknown commands
    application.add_handler(MessageHandler(filters.COMMAND, unknown_command))
    
    return application

async def post_init(application: Application):
    """Tasks to run after bot initialization"""
    # Set up commands
    await setup_commands(application)
    
    # Set up scheduler for checking unfollowers
    async def job_callback(result):
        await notify_unfollowers(application.bot, result)
    
    scheduler = SchedulerService(application.bot, job_callback)
    scheduler.start()
    
    # Store scheduler in application context for later access
    application.bot_data["scheduler"] = scheduler
    
    logger.info("Bot fully initialized")

def main():
    """Main function to start the bot"""
    logger.info("Starting bot...")
    
    # Check if token is available
    if not TOKEN:
        logger.error("No token provided! Please set TELEGRAM_BOT_TOKEN in environment variables.")
        sys.exit(1)
    
    # Create and run the application
    application = create_application()
    
    # Set post init callback
    application.post_init = post_init
    
    # Run the bot
    application.run_polling()
    
    logger.info("Bot stopped")

if __name__ == "__main__":
    main() 