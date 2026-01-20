#!/usr/bin/env python3
"""
Telegram Bot - Main Entry Point

A Telegram bot that interfaces with OpenCode AI assistant through the Wrapper Server.
Supports text messages, voice notes, images, and documents.

Usage:
    python bot.py                    # Run with polling
    python bot.py --webhook          # Run in webhook mode

Commands:
    /start   - Start the bot and create a session
    /help    - Show help message
    /new     - Create a new session (ends current one)
    /status  - Show current session status
    /end     - End the current session
    /cancel  - Cancel current operation
"""

import sys
from pathlib import Path

# Ensure src is in path for imports
_src_path = Path(__file__).parent
if str(_src_path) not in sys.path:
    sys.path.insert(0, str(_src_path))

from telegram import (
    BotCommand,
    BotCommandScopeAllChatAdministrators,
    BotCommandScopeAllGroupChats,
    BotCommandScopeAllPrivateChats,
    Update,
)
from telegram.ext import (
    Application,
    ChatMemberHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)


# Bot commands to register with Telegram for autocomplete
BOT_COMMANDS = [
    BotCommand("start", "Start the bot and create a session"),
    BotCommand("help", "Show help message"),
    BotCommand("new", "Create a new session"),
    BotCommand("status", "Show current session status"),
    BotCommand("end", "End the current session"),
    BotCommand("cancel", "Cancel current operation"),
]


# Bot identity (initialized in post_init)
BOT_USERNAME = ""


async def post_init(application: Application) -> None:
    """Register bot commands with Telegram for both private and group chats."""
    global BOT_USERNAME

    # Get bot info
    me = await application.bot.get_me()
    BOT_USERNAME = me.username
    logger.info(f"Bot initialized as @{BOT_USERNAME}")

    # Register commands for private chats
    await application.bot.set_my_commands(BOT_COMMANDS, scope=BotCommandScopeAllPrivateChats())
    # Register commands for group chats
    await application.bot.set_my_commands(BOT_COMMANDS, scope=BotCommandScopeAllGroupChats())
    # Register commands for group administrators (ensures visibility)
    await application.bot.set_my_commands(BOT_COMMANDS, scope=BotCommandScopeAllChatAdministrators())
    logger.info("Bot commands registered with Telegram for private chats, groups, and admins")

from config import get_config
from logger import setup_logging, get_logger
from session_manager import get_session_manager
from keyboards import (
    get_main_menu_keyboard,
    get_session_keyboard,
    get_help_keyboard,
)
from wrapper_client import WrapperClient, WrapperAPIError
from event_handler import get_event_handler, EventHandler


# Configure logging
setup_logging()
logger = get_logger()


# ============================================================================
# Chat Access Control
# ============================================================================

def is_chat_allowed(chat_id: int) -> bool:
    """
    Check if a chat ID is allowed based on security configuration.

    Returns True if:
    - No valid allowed_chat_ids are configured (all chats allowed)
    - The chat_id is in the allowed list
    """
    config = get_config()
    allowed_ids = config.security.allowed_chat_ids

    logger.info(f"Allowed chat IDs: {allowed_ids}")
    logger.info(f"Chat ID: {chat_id}")

    # Filter out invalid IDs (0 or None) before checking
    valid_ids = [cid for cid in allowed_ids if cid and cid != 0]

    # If no restrictions configured, allow all chats
    if not valid_ids:
        return True

    # Check if chat_id is in allowed list
    if chat_id in valid_ids:
        return True

    # Handle Supergroup ID mismatch (Telegram Web vs Bot API)
    # If config has -12345678 but API sends -10012345678, allow it
    s_chat_id = str(chat_id)
    if s_chat_id.startswith("-100"):
        short_id = "-" + s_chat_id[4:]
        if int(short_id) in valid_ids:
            return True

    return False


def get_chat_type(chat_id: int) -> str:
    """Determine if a chat ID is a group (negative) or private (positive)"""
    return "group" if chat_id < 0 else "private"


def is_chat_type_allowed(chat_id: int) -> bool:
    """Check if the chat type (group/private) is allowed"""
    config = get_config()
    mode = config.security.mode

    if mode == "both":
        return True

    chat_type = get_chat_type(chat_id)
    return chat_type == mode


async def check_and_handle_restricted_chat(update: Update) -> bool:
    """
    Check if chat is allowed. If not, send error message.

    Returns True if chat is blocked, False if allowed to proceed.
    """
    if not update.effective_chat:
        return False


# ============================================================================
# User Access Control
# ============================================================================

def is_user_allowed(user_id: int) -> bool:
    """
    Check if a user ID is in the allowed users list.

    Returns True if:
    - No allowed_user_ids are configured (all users allowed)
    - The user_id is in the allowed list
    """
    config = get_config()
    allowed_ids = config.security.allowed_user_ids

    # Filter out invalid IDs (0 or None)
    valid_ids = [uid for uid in allowed_ids if uid and uid != 0]

    # If no user restrictions configured, allow all users
    if not valid_ids:
        return True

    # Check if user_id is in allowed list
    return user_id in valid_ids


async def check_and_handle_unauthorized_user(update: Update) -> bool:
    """
    Check if user is authorized. If not, send error message.

    Returns True if user is unauthorized, False if allowed to proceed.
    """
    if not update.effective_user:
        return False

    user_id = update.effective_user.id

    logger.info(f"Checking access for user {user_id}")

    user_name = update.effective_user.full_name or update.effective_user.username or "Unknown"
    config = get_config()

    # If no user restrictions configured, allow all users
    if not config.security.allowed_user_ids:
        return False

    # Check if user is in allowed list
    if not is_user_allowed(user_id):
        logger.warning(f"Access denied for user {user_id} ({user_name}). Not in allowed_user_ids: {config.security.allowed_user_ids}")
        if update.message:
            await update.message.reply_text(
                "❌ You are not authorized to use this bot.\n\n"
                f"User ID: <code>{user_id}</code>\n"
                "Please contact the bot administrator.",
                parse_mode="HTML"
            )
        return True

    return False

    chat_id = update.effective_chat.id
    chat_type = update.effective_chat.type
    config = get_config()

    logger.debug(f"Checking access for {chat_type} chat {chat_id}")

    # Check chat type (group vs private)
    if not is_chat_type_allowed(chat_id):
        return True # Handled in commands or handle_message

    # Check allowed list
    if not is_chat_allowed(chat_id):
        if config.security.block_unknown:
            logger.warning(f"Access denied for {chat_type} {chat_id}. Not in allowed_chat_ids: {config.security.allowed_chat_ids}")
            if update.message:
                await update.message.reply_text(
                    "❌ This bot is not authorized to operate in this chat.\n\n"
                    f"Chat ID: <code>{chat_id}</code>\n"
                    "Please add this ID to your <code>allowed_chat_ids</code> in configuration.",
                    parse_mode="HTML"
                )
            return True

    return False


# ============================================================================
# Command Handlers
# ============================================================================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /start command.

    Creates a new session and welcomes the user.
    """
    chat_id = update.effective_chat.id

    # Check if chat is allowed
    config = get_config()
    if not is_chat_type_allowed(chat_id):
        mode = config.security.mode
        msg = "❌ This bot is configured to only work in groups." if mode == "group" else "❌ This bot is configured to only work in private chats."
        await update.message.reply_text(msg)
        return

    if not is_chat_allowed(chat_id):
        await update.message.reply_text(
            "❌ This bot is not authorized to operate in this chat.\n\n"
            "Please contact the bot administrator with Chat ID: <code>" + str(chat_id) + "</code>",
            parse_mode="HTML",
        )
        return

    # Check if user is authorized
    if await check_and_handle_unauthorized_user(update):
        return

    user = update.effective_user

    session_manager = get_session_manager()

    # Check if user already has an active session
    existing_session = session_manager.get_session(chat_id)

    if existing_session and existing_session.is_active:
        await update.message.reply_text(
            f"Welcome back, {user.mention_html()}!\n\n"
            "You already have an active session. You can continue where you left off "
            "or use /new to start a fresh session.",
            reply_markup=get_session_keyboard(),
            parse_mode="HTML",
        )
    else:
        # Create new session
        try:
            client = WrapperClient()
            config = get_config()
            session_data = await client.start_session(
                chat_id,
                agent=config.session.default_agent or None
            )

            session_manager.get_or_create(
                chat_id=chat_id,
                opencode_session_id=session_data["session_id"],
                agent=config.session.default_agent or None,
            )

            await update.message.reply_text(
                f"Hello, {user.mention_html()}! I'm your AI assistant.\n\n"
                "I can help you with analysis, research, coding, and more. "
                "Just send me a message and I'll assist you.",
                reply_markup=get_main_menu_keyboard(),
                parse_mode="HTML",
            )
            logger.info(f"New session started for chat {chat_id}")
        except WrapperAPIError as e:
            logger.error(f"Failed to start session: {e}")
            await update.message.reply_text(
                "Sorry, I couldn't start a new session. Please try again later.",
            )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command"""
    # Check if user is authorized
    if await check_and_handle_unauthorized_user(update):
        return

    help_text = """
I'm your AI assistant. Here's what I can do:

/start   - Start a new conversation
/new    - Start a fresh session (ends current one)
/status  - Check your current session
/end     - End the current session
/help    - Show this help message

You can also:
- Send text messages for analysis
- Send voice notes (I'll transcribe them)
- Send images for analysis
- Send documents for processing

How can I help you today?
    """.strip()

    await update.message.reply_text(
        help_text,
        reply_markup=get_help_keyboard(),
    )


async def new_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /new command.

    Creates a new session, ending the current one if active.
    """
    # Check if user is authorized
    if await check_and_handle_unauthorized_user(update):
        return

    chat_id = update.effective_chat.id
    user = update.effective_user

    session_manager = get_session_manager()
    existing_session = session_manager.get_session(chat_id)

    if existing_session and existing_session.is_active:
        # End old session
        session_manager.set_active(chat_id, False)
        logger.info(f"Ended session for chat {chat_id}")

    # Create new session
    try:
        client = WrapperClient()
        config = get_config()
        session_data = await client.start_session(
            chat_id,
            agent=config.session.default_agent or None
        )

        session = session_manager.get_or_create(
            chat_id=chat_id,
            opencode_session_id=session_data["session_id"],
            agent=config.session.default_agent or None,
        )

        await update.message.reply_text(
            f"New session started, {user.mention_html()}!\n\n"
            "What would you like to work on?",
            reply_markup=get_session_keyboard(),
            parse_mode="HTML",
        )
        logger.info(f"New session created for chat {chat_id}")
    except WrapperAPIError as e:
        logger.error(f"Failed to create new session: {e}")
        await update.message.reply_text(
            "Sorry, I couldn't create a new session. Please try again.",
        )


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /status command"""
    # Check if user is authorized
    if await check_and_handle_unauthorized_user(update):
        return

    chat_id = update.effective_chat.id
    session_manager = get_session_manager()
    session = session_manager.get_session(chat_id)

    if not session or not session.is_active:
        await update.message.reply_text(
            "You don't have an active session. Use /start to begin.",
            reply_markup=get_main_menu_keyboard(),
        )
        return

    status_text = f"""
📊 Session Status

Session ID: {session.opencode_session_id or 'N/A'}
Started: {session.created_at.strftime('%Y-%m-%d %H:%M') if session.created_at else 'Unknown'}
Last Activity: {session.last_activity.strftime('%Y-%m-%d %H:%M') if session.last_activity else 'Unknown'}
Agent: {session.agent or 'Default'}

You can continue the conversation or use /end to close this session.
    """.strip()

    await update.message.reply_text(
        status_text,
        reply_markup=get_session_keyboard(),
    )


async def end_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /end command"""
    # Check if user is authorized
    if await check_and_handle_unauthorized_user(update):
        return

    chat_id = update.effective_chat.id
    user = update.effective_user

    session_manager = get_session_manager()
    session = session_manager.get_session(chat_id)

    if session:
        session_manager.set_active(chat_id, False)
        logger.info(f"Session ended for chat {chat_id}")

    await update.message.reply_text(
        f"Session ended, {user.mention_html()}.\n\n"
        "Use /start to begin a new conversation whenever you're ready.",
        reply_markup=get_main_menu_keyboard(),
        parse_mode="HTML",
    )


# ============================================================================
# Message Handlers
# ============================================================================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle all text messages.

    In groups, the bot only responds if:
    1. It is mentioned (@BotName)
    2. It is a reply to one of the bot's messages
    """
    if not update.message or not update.message.text:
        return

    chat_id = update.effective_chat.id
    chat_type = update.effective_chat.type
    message_text = update.message.text.strip()
    is_group = chat_type in ["group", "supergroup"]

    # Ignore commands (they have their own handlers)
    if message_text.startswith("/"):
        return

    # In groups, check if we should respond
    should_respond = not is_group  # Always respond in private chats

    if is_group:
        # Check for mention
        bot_mention = f"@{BOT_USERNAME}"
        if bot_mention in message_text:
            should_respond = True
            # Clean up message (remove mention)
            message_text = message_text.replace(bot_mention, "").strip()

        # Check if it's a reply to the bot
        elif update.message.reply_to_message and update.message.reply_to_message.from_user.id == context.bot.id:
            should_respond = True

    if not should_respond:
        return

    # Logging move for visibility
    logger.info(f"Processing message in {chat_type} {chat_id}")

    # Check if chat is allowed
    if await check_and_handle_restricted_chat(update):
        return

    # Check if user is authorized
    if await check_and_handle_unauthorized_user(update):
        return

    session_manager = get_session_manager()
    session = session_manager.get_session(chat_id)

    # Check for active session
    if not session or not session.is_active:
        await update.message.reply_text(
            "No active session. Use /start to begin.",
            reply_markup=get_main_menu_keyboard(),
        )
        return

    # Show typing indicator
    await context.bot.send_chat_action(chat_id=chat_id, action="typing")

    # Send initial "Processing..." message that we'll update with events
    status_message = await update.message.reply_text(
        "⏳ Processing your message...",
    )

    # Send message and stream events
    try:
        client = WrapperClient()

        # First, send the message to OpenCode (synchronous API)
        response = await client.send_message(
            session_id=session.opencode_session_id,
            message=message_text,
            chat_id=chat_id,
            agent=session.agent,
        )

        # Update last activity
        session_manager.update_session(chat_id)

        # Get response text
        response_text = response.get("response", "")

        if response_text:
            # edit_text doesn't support ReplyKeyboardMarkup - users can still use commands
            await status_message.edit_text(
                response_text,
                parse_mode="Markdown",
            )
        else:
            await status_message.edit_text(
                "I couldn't get a response. Please try again.",
            )

        logger.info(f"Message sent to chat {chat_id}")

    except WrapperAPIError as e:
        logger.error(f"Failed to send message: {e}")
        await status_message.edit_text(
            "Sorry, I couldn't process your message. Please try again.",
        )


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle voice messages"""
    if not update.message.voice:
        return

    chat_id = update.effective_chat.id

    # Check if chat is allowed
    if await check_and_handle_restricted_chat(update):
        return

    # Check if user is authorized
    if await check_and_handle_unauthorized_user(update):
        return

    session_manager = get_session_manager()
    session = session_manager.get_session(chat_id)

    if not session or not session.is_active:
        await update.message.reply_text(
            "No active session. Use /start to begin.",
        )
        return

    # Download voice file
    voice = update.message.voice
    voice_file = await context.bot.get_file(voice.file_id)
    voice_path = f"/tmp/{voice.file_id}.ogg"
    await voice_file.download_to_drive(voice_path)

    # Show typing indicator
    await context.bot.send_chat_action(chat_id=chat_id, action="typing")

    try:
        client = WrapperClient()
        response = await client.send_audio(
            session_id=session.opencode_session_id,
            audio_path=voice_path,
            chat_id=chat_id,
        )

        await update.message.reply_text(
            response.get("response", "Voice message processed."),
            reply_markup=get_session_keyboard(),
        )

    except WrapperAPIError as e:
        logger.error(f"Failed to process voice: {e}")
        await update.message.reply_text(
            "Sorry, I couldn't process your voice message.",
        )


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle photo messages"""
    if not update.message.photo:
        return

    chat_id = update.effective_chat.id

    # Check if chat is allowed
    if await check_and_handle_restricted_chat(update):
        return

    # Check if user is authorized
    if await check_and_handle_unauthorized_user(update):
        return

    session_manager = get_session_manager()
    session = session_manager.get_session(chat_id)

    if not session or not session.is_active:
        await update.message.reply_text(
            "No active session. Use /start to begin.",
        )
        return

    # Download photo (use highest resolution)
    photo = update.message.photo[-1]
    photo_file = await context.bot.get_file(photo.file_id)
    photo_path = f"/tmp/{photo.file_id}.jpg"
    await photo_file.download_to_drive(photo_path)

    # Show typing indicator
    await context.bot.send_chat_action(chat_id=chat_id, action="typing")

    try:
        client = WrapperClient()
        response = await client.send_image(
            session_id=session.opencode_session_id,
            image_path=photo_path,
            chat_id=chat_id,
        )

        await update.message.reply_text(
            response.get("response", "Image processed."),
            reply_markup=get_session_keyboard(),
        )

    except WrapperAPIError as e:
        logger.error(f"Failed to process image: {e}")
        await update.message.reply_text(
            "Sorry, I couldn't process your image.",
        )


# ============================================================================
# Group Event Handlers
# ============================================================================

async def handle_my_chat_member(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the bot being added to or removed from a group."""
    result = update.my_chat_member
    chat = result.chat

    # Check if the bot was added
    if result.new_chat_member.status in ["member", "administrator"]:
        logger.info(f"Bot added to chat: {chat.title} ({chat.id})")

        # Check if chat is allowed
        if not is_chat_allowed(chat.id):
            await context.bot.send_message(
                chat_id=chat.id,
                text=(
                    "🤖 Hello! I've been added to this group, but I'm not authorized to operate here yet.\n\n"
                    f"Please contact the administrator and provide this Chat ID: <code>{chat.id}</code>"
                ),
                parse_mode="HTML"
            )
            return

        await context.bot.send_message(
            chat_id=chat.id,
            text=(
                f"🤖 Hello! I'm your AI assistant, now active in <b>{chat.title}</b>.\n\n"
                "To talk to me, just mention me like @"+BOT_USERNAME+" or reply to my messages.\n"
                "Use /start to begin a new session."
            ),
            parse_mode="HTML"
        )


# ============================================================================
# Error Handler
# ============================================================================

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle errors"""
    logger.error(f"Bot error: {context.error}")

    if update and update.message:
        await update.message.reply_text(
            "An error occurred. Please try again or use /help.",
        )


# ============================================================================
# Main Entry Point
# ============================================================================

def run_polling():
    """Run bot in polling mode"""
    config = get_config()

    if not config.telegram.bot_token:
        logger.error("TELEGRAM_BOT_TOKEN not configured!")
        sys.exit(1)

    logger.info("Starting Telegram bot in polling mode...")

    app = Application.builder().token(config.telegram.bot_token).post_init(post_init).build()

    # Register command handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("new", new_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("end", end_command))
    app.add_handler(CommandHandler("cancel", end_command))

    # Register group event handlers
    app.add_handler(ChatMemberHandler(handle_my_chat_member, ChatMemberHandler.MY_CHAT_MEMBER))

    # Register message handlers
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    # Register error handler
    app.add_error_handler(error_handler)

    # Run polling
    app.run_polling()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Telegram Bot for OpenCode")
    parser.add_argument(
        "--webhook",
        action="store_true",
        help="Run in webhook mode instead of polling",
    )
    args = parser.parse_args()

    if args.webhook:
        from webhook_handler import run_webhook
        run_webhook()
    else:
        run_polling()
