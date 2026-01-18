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

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from config import get_config
from logger import setup_logging, get_logger
from session_manager import get_session_manager
from keyboards import (
    get_main_menu_keyboard,
    get_session_keyboard,
    get_help_keyboard,
)
from wrapper_client import WrapperClient, WrapperAPIError


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
    
    # Filter out invalid IDs (0 or None) before checking
    valid_ids = [cid for cid in allowed_ids if cid and cid != 0]
    
    # If no restrictions configured, allow all chats
    if not valid_ids:
        return True
    
    # Check if chat_id is in allowed list
    return chat_id in valid_ids


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
    chat_id = update.effective_chat.id
    config = get_config()

    # Check chat type (group vs private)
    if not is_chat_type_allowed(chat_id):
        await update.message.reply_text(
            "❌ This bot is configured to only work in specific chat types.\n\n"
            "Please use the bot in the configured chat type.",
        )
        logger.warning(f"Chat {chat_id} rejected: wrong chat type")
        return True

    # Check allowed list
    if not is_chat_allowed(chat_id):
        if config.security.block_unknown:
            await update.message.reply_text(
                "❌ This bot is not authorized to operate in this chat.\n\n"
                "Please contact the bot administrator.",
            )
            logger.warning(f"Chat {chat_id} rejected: not in allowed list")
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
        await update.message.reply_text(
            "❌ This bot only works in groups.",
        )
        return

    if not is_chat_allowed(chat_id):
        await update.message.reply_text(
            "❌ This bot is not authorized for this chat.",
        )
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
            session_data = await client.start_session(chat_id)

            session_manager.get_or_create(
                chat_id=chat_id,
                opencode_session_id=session_data["session_id"],
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
        session_data = await client.start_session(chat_id)

        session = session_manager.get_or_create(
            chat_id=chat_id,
            opencode_session_id=session_data["session_id"],
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

    Forwards the message to OpenCode via the Wrapper Server.
    """
    if not update.message or not update.message.text:
        return

    chat_id = update.effective_chat.id
    user = update.effective_user
    message_text = update.message.text.strip()

    # Ignore commands (they have their own handlers)
    if message_text.startswith("/"):
        return

    # Check if chat is allowed
    if await check_and_handle_restricted_chat(update):
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

    # Send message to wrapper server
    try:
        client = WrapperClient()
        response = await client.send_message(
            session_id=session.opencode_session_id,
            message=message_text,
            chat_id=chat_id,
        )

        # Update last activity
        session_manager.update_session(chat_id)

        # Send response
        await update.message.reply_text(
            response.get("response", "I couldn't get a response. Please try again."),
            reply_markup=get_session_keyboard(),
            parse_mode="Markdown",
        )
        logger.info(f"Message sent to chat {chat_id}")

    except WrapperAPIError as e:
        logger.error(f"Failed to send message: {e}")
        await update.message.reply_text(
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

    app = Application.builder().token(config.telegram.bot_token).build()

    # Register command handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("new", new_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("end", end_command))
    app.add_handler(CommandHandler("cancel", end_command))

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
