from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from loguru import logger
from src.services.user_service import UserService
from src.services.tracking_service import TrackingService

# States for conversation
WAITING_FOR_USERNAME = 1

# Initialize services
user_service = UserService()
tracking_service = TrackingService()

# Command handlers
async def track_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /track command - start tracking a new account"""
    # Check if command has arguments
    if context.args and len(context.args) > 0:
        # If argument is provided, use it as the username
        instagram_username = context.args[0]
        return await handle_track_username(update, context, instagram_username)
    else:
        # Otherwise ask for username
        await update.message.reply_text(
            "📝 Please enter the Instagram username you want to track:"
        )
        return WAITING_FOR_USERNAME

async def track_username_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for username input in tracking conversation"""
    instagram_username = update.message.text.strip()
    return await handle_track_username(update, context, instagram_username)

async def handle_track_username(update: Update, context: ContextTypes.DEFAULT_TYPE, instagram_username: str):
    """Process the username and start tracking"""
    chat_id = str(update.effective_chat.id)
    
    # Remove '@' if present
    if instagram_username.startswith('@'):
        instagram_username = instagram_username[1:]
    
    # Get user ID
    user = user_service.get_or_create_user(chat_id)
    if not user:
        await update.message.reply_text("❌ Failed to retrieve your user information. Please try again.")
        return ConversationHandler.END
    
    # Send processing message
    processing_message = await update.message.reply_text(
        f"⏳ Processing your request to track @{instagram_username}..."
    )
    
    # Start tracking
    success, message = tracking_service.start_tracking(user.id, instagram_username)
    
    # Edit the processing message with the result
    if success:
        if "private" in message.lower() and "follow request" in message.lower():
            # For private accounts with pending follow requests
            keyboard = [
                [InlineKeyboardButton("✅ Подтвердить", callback_data=f"confirm_follow:{instagram_username}")],
                [InlineKeyboardButton("❌ Отменить", callback_data=f"stop_tracking_username:{instagram_username}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await processing_message.edit_text(
                f"🔒 @{instagram_username} - это приватный аккаунт.\n\n"
                f"1. Мы отправили запрос на подписку с аккаунта @biljon10\n"
                f"2. Пожалуйста, ПРИМИТЕ запрос на подписку в Instagram\n"
                f"3. После принятия, нажмите кнопку '✅ Подтвердить' ниже",
                reply_markup=reply_markup
            )
        else:
            # For public accounts
            await processing_message.edit_text(
                f"✅ Успешно начат трекинг @{instagram_username}!\n\n"
                f"Вы будете получать уведомления, когда кто-то отпишется от этого аккаунта."
            )
    else:
        # Handle errors
        await processing_message.edit_text(
            f"❌ Не удалось отследить @{instagram_username}.\n"
            f"Причина: {message}"
        )
    
    return ConversationHandler.END

async def handle_confirm_follow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle confirmation that a follow request was accepted"""
    query = update.callback_query
    await query.answer()
    
    # Extract the account name from callback data
    callback_data = query.data
    instagram_username = callback_data.split(':')[1]
    
    chat_id = str(update.effective_chat.id)
    user = user_service.get_or_create_user(chat_id)
    
    # Find the tracked account
    session = get_session()
    tracked_account = session.query(TrackedAccount).filter_by(
        user_id=user.id,
        instagram_username=instagram_username
    ).first()
    close_session(session)
    
    if not tracked_account:
        await query.edit_message_text(
            f"❌ Error: Couldn't find tracked account for @{instagram_username}."
        )
        return
    
    # Update the message to show processing
    await query.edit_message_text(
        f"⏳ Confirming follow for @{instagram_username} and loading initial followers..."
    )
    
    # Process the confirmation
    success, message = tracking_service.confirm_follow_accepted(tracked_account.id)
    
    if success:
        await query.edit_message_text(
            f"✅ Success! Now tracking @{instagram_username}.\n\n"
            f"You will be notified when someone unfollows this account."
        )
    else:
        # For failed attempts, offer a retry button
        keyboard = [
            [InlineKeyboardButton("Try Again", callback_data=f"confirm_follow:{instagram_username}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"❌ Failed to confirm follow for @{instagram_username}.\n"
            f"Reason: {message}",
            reply_markup=reply_markup
        )

async def accounts_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /accounts command - show tracked accounts"""
    chat_id = str(update.effective_chat.id)
    user = user_service.get_or_create_user(chat_id)
    
    # Get tracked accounts
    tracked_accounts = tracking_service.get_tracked_accounts(user.id)
    
    if not tracked_accounts or len(tracked_accounts) == 0:
        await update.message.reply_text(
            "📝 You're not tracking any accounts yet.\n"
            "Use /track command to start tracking an Instagram account."
        )
        return
    
    # Build response message and keyboard
    message = "📋 *Your Tracked Accounts:*\n\n"
    keyboard = []
    
    for account in tracked_accounts:
        status = "🔒 Private" if account.is_private else "🔓 Public"
        pending = " (Pending follow acceptance)" if account.follow_requested else ""
        
        message += f"• @{account.instagram_username} - {status}{pending}\n"
        keyboard.append([
            InlineKeyboardButton(f"Stop tracking @{account.instagram_username}", 
                               callback_data=f"stop_tracking:{account.id}")
        ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        message,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def handle_stop_tracking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle stopping tracking for an account"""
    query = update.callback_query
    await query.answer()
    
    # Extract the account ID from callback data
    callback_data = query.data
    account_id = int(callback_data.split(':')[1])
    
    chat_id = str(update.effective_chat.id)
    user = user_service.get_or_create_user(chat_id)
    
    # Stop tracking
    success, message = tracking_service.stop_tracking(user.id, account_id)
    
    if success:
        await query.edit_message_text(
            f"✅ {message}\n\n"
            f"Use /accounts to view your remaining tracked accounts."
        )
    else:
        await query.edit_message_text(
            f"❌ Failed to stop tracking.\n"
            f"Reason: {message}"
        )

# Callback for handling tracking account button
async def handle_track_account_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the 'Track Account' button click"""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "📝 Please send me the Instagram username you want to track:",
    )
    
    return WAITING_FOR_USERNAME

# Callback for handling list accounts button
async def handle_list_accounts_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the 'My Tracked Accounts' button click"""
    query = update.callback_query
    await query.answer()
    
    # Get user ID from chat
    chat_id = str(update.effective_chat.id)
    user = user_service.get_or_create_user(chat_id)
    
    # Get tracked accounts
    tracked_accounts = tracking_service.get_tracked_accounts(user.id)
    
    if not tracked_accounts or len(tracked_accounts) == 0:
        await query.edit_message_text(
            "📝 You're not tracking any accounts yet.\n"
            "Use /track command to start tracking an Instagram account."
        )
        return
    
    # Build response message and keyboard
    message = "📋 *Your Tracked Accounts:*\n\n"
    keyboard = []
    
    for account in tracked_accounts:
        status = "🔒 Private" if account.is_private else "🔓 Public"
        pending = " (Pending follow acceptance)" if account.follow_requested else ""
        
        message += f"• @{account.instagram_username} - {status}{pending}\n"
        keyboard.append([
            InlineKeyboardButton(f"Stop tracking @{account.instagram_username}", 
                               callback_data=f"stop_tracking:{account.id}")
        ])
    
    # Add a back button
    keyboard.append([InlineKeyboardButton("◀️ Back to Main Menu", callback_data="start")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Update the existing message
    await query.edit_message_text(
        message,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

# Handle unfollower notifications from scheduler
async def notify_unfollowers(bot, result):
    """Send notifications about unfollowers"""
    try:
        user_id = result["user_id"]
        instagram_username = result["instagram_username"]
        unfollowers = result["unfollowers"]
        
        # Get user's chat_id
        session = get_session()
        user = session.query(User).filter_by(id=user_id).first()
        close_session(session)
        
        if not user:
            logger.error(f"User not found for ID: {user_id}")
            return
        
        # Generate message
        message = f"🔔 *Unfollower Alert for @{instagram_username}*\n\n"
        
        if len(unfollowers) == 1:
            unfollower = unfollowers[0]
            message += f"*{unfollower['username']}* ({unfollower['full_name']}) has unfollowed you."
        else:
            message += f"*{len(unfollowers)} people* have unfollowed you:\n\n"
            for idx, unfollower in enumerate(unfollowers, 1):
                message += f"{idx}. *{unfollower['username']}* ({unfollower['full_name']})\n"
        
        # Send notification
        await bot.send_message(
            chat_id=user.chat_id,
            text=message,
            parse_mode="Markdown"
        )
        
        logger.info(f"Sent unfollower notification to user {user.chat_id} for account {instagram_username}")
        
    except Exception as e:
        logger.error(f"Error sending unfollower notification: {e}")

async def handle_stop_tracking_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle stopping tracking by username"""
    query = update.callback_query
    await query.answer()
    
    # Extract the username from callback data
    callback_data = query.data
    instagram_username = callback_data.split(':')[1]
    
    chat_id = str(update.effective_chat.id)
    user = user_service.get_or_create_user(chat_id)
    
    # Get account ID by username
    session = get_session()
    tracked_account = session.query(TrackedAccount).filter_by(
        user_id=user.id,
        instagram_username=instagram_username
    ).first()
    
    if tracked_account:
        account_id = tracked_account.id
        close_session(session)
        
        # Stop tracking
        success, message = tracking_service.stop_tracking(user.id, account_id)
        
        if success:
            await query.edit_message_text(
                f"✅ Отслеживание @{instagram_username} отменено."
            )
        else:
            await query.edit_message_text(
                f"❌ Не удалось отменить отслеживание.\n"
                f"Причина: {message}"
            )
    else:
        close_session(session)
        await query.edit_message_text(
            f"❌ Аккаунт @{instagram_username} не найден в списке отслеживаемых."
        )

from src.db.models import TrackedAccount, User
from src.db.session import get_session, close_session 