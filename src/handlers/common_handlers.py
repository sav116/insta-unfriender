from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from loguru import logger
from src.services.user_service import UserService

# Initialize services
user_service = UserService()

# Command handlers
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /start command"""
    chat_id = str(update.effective_chat.id)
    username = update.effective_user.username
    
    # Get or create user
    user_service.get_or_create_user(chat_id, username)
    
    # Create welcome message with inline keyboard
    keyboard = [
        [InlineKeyboardButton("Track Account", callback_data="track_account")],
        [InlineKeyboardButton("My Tracked Accounts", callback_data="list_accounts")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "👋 Welcome to Instagram Unfriender Bot!\n\n"
        "I can help you track unfollowers from Instagram accounts.\n"
        "Use the buttons below to get started or type /help for more info.",
        reply_markup=reply_markup
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /help command"""
    chat_id = str(update.effective_chat.id)
    is_admin = user_service.is_admin(chat_id)
    
    help_text = (
        "📋 *Instagram Unfriender Bot Help*\n\n"
        "*Commands:*\n"
        "/start - Start the bot\n"
        "/help - Show this help message\n"
        "/track - Track a new Instagram account\n"
        "/accounts - List your tracked accounts\n\n"
        
        "*How it works:*\n"
        "1. Use /track to start tracking an account\n"
        "2. For public accounts, tracking starts immediately\n"
        "3. For private accounts, you'll need to accept a follow request from our technical account\n"
        "4. The bot checks for unfollowers periodically and notifies you\n\n"
    )
    
    if is_admin:
        admin_help = (
            "*Admin Commands:*\n"
            "/set_tech_account - Change technical Instagram account\n"
            "/set_check_interval - Change check frequency\n"
            "/stats - Show bot statistics\n\n"
        )
        help_text += admin_help
    
    await update.message.reply_text(help_text, parse_mode="Markdown")

async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for unknown commands"""
    await update.message.reply_text(
        "Sorry, I don't understand that command. Use /help to see available commands."
    )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors in the bot"""
    logger.error(f"Update {update} caused error {context.error}")
    
    # Send error message to user if applicable
    if update and update.effective_chat:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Sorry, something went wrong. Please try again later."
        )
    
    # Log more detailed error
    logger.error(f"Exception in update {update}: {context.error}", exc_info=context.error) 