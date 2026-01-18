#!/usr/bin/env python3
"""
Webhook Handler Module

FastAPI application for handling Telegram webhooks.
Used in production instead of polling mode.
"""

import sys
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from loguru import logger
from pydantic import BaseModel
from telegram import Update
from telegram.error import TelegramError
from telegram.ext import Application, ApplicationBuilder

# Ensure src is in path for imports
_src_path = Path(__file__).parent
if str(_src_path) not in sys.path:
    sys.path.insert(0, str(_src_path))

from config import get_config
from session_manager import get_session_manager
from wrapper_client import WrapperClient, WrapperAPIError
from keyboards import get_main_menu_keyboard, get_session_keyboard


# Configure logging
config = get_config()
logger.remove()
logger.add(
    lambda msg: print(msg, end=""),
    format=config.logging.format,
    level=config.logging.level,
    colorize=True,
)


# Global Application instance
_telegram_app: Application = None


async def setup_telegram_app() -> Application:
    """Setup and return Telegram Application instance"""
    global _telegram_app
    
    if _telegram_app is None:
        _telegram_app = (
            ApplicationBuilder()
            .token(config.telegram.bot_token)
            .concurrent_updates(1)
            .build()
        )
        await _telegram_app.initialize()
    
    return _telegram_app


# Lifespan context
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    logger.info("Starting webhook handler...")
    
    try:
        await setup_telegram_app()
        logger.success("Telegram application initialized")
    except Exception as e:
        logger.error(f"Failed to initialize Telegram app: {e}")
    
    yield
    
    logger.info("Shutting down webhook handler...")
    if _telegram_app:
        await _telegram_app.shutdown()


# Create FastAPI app
app = FastAPI(
    title="Telegram Webhook Handler",
    description="Webhook endpoint for Telegram bot updates",
    version="1.0.0",
    lifespan=lifespan,
)


# ============================================================================
# Pydantic Models
# ============================================================================

class WebhookResponse(BaseModel):
    """Response for webhook processing"""
    status: str
    session_id: str = None
    response: str = None


# ============================================================================
# Exception Handlers
# ============================================================================

@app.exception_handler(WrapperAPIError)
async def wrapper_api_error_handler(request: Request, exc: WrapperAPIError):
    """Handle Wrapper API errors"""
    logger.error(f"Wrapper API Error: {exc.message}")
    return JSONResponse(
        status_code=exc.status_code or 500,
        content={"error": exc.message},
    )


@app.exception_handler(TelegramError)
async def telegram_error_handler(request: Request, exc: TelegramError):
    """Handle Telegram errors"""
    logger.error(f"Telegram Error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "Telegram API error"},
    )


# ============================================================================
# Webhook Endpoint
# ============================================================================

@app.post(f"/{config.webhook.path}")
async def telegram_webhook(request: Request) -> WebhookResponse:
    """
    Telegram webhook endpoint.
    
    Receives updates from Telegram and processes them.
    """
    data = await request.json()
    
    # Parse Telegram update
    try:
        update = Update.de_json(data, _telegram_app.bot)
    except Exception as e:
        logger.error(f"Failed to parse update: {e}")
        raise HTTPException(status_code=400, detail="Invalid update format")
    
    if not update:
        raise HTTPException(status_code=400, detail="No update found")
    
    # Process the update
    async with _telegram_app:
        await _telegram_app.process_update(update)
    
    # Return success (Telegram doesn't need the actual response)
    return WebhookResponse(status="ok")


@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "telegram_bot": "initialized" if _telegram_app else "not initialized",
    }


# ============================================================================
# Main Entry Point
# ============================================================================

def run_webhook():
    """Run the webhook handler"""
    import uvicorn
    
    if not config.telegram.bot_token:
        logger.error("TELEGRAM_BOT_TOKEN not configured!")
        return
    
    if not config.webhook.enabled:
        logger.warning("WEBHOOK_ENABLED is false. Starting anyway...")
    
    # Set webhook URL in Telegram
    async def set_webhook():
        app = await setup_telegram_app()
        webhook_url = f"https://{config.webhook.host}/{config.webhook.path}"
        
        try:
            await app.bot.set_webhook(webhook_url)
            logger.success(f"Webhook set to: {webhook_url}")
        except TelegramError as e:
            logger.error(f"Failed to set webhook: {e}")
    
    # Run the setup and server
    import threading
    
    # Set webhook in separate thread
    loop = asyncio.new_event_loop()
    threading.Thread(target=loop.run_until_complete, args=(set_webhook(),)).start()
    
    # Run FastAPI server
    print(f"""
╔════════════════════════════════════════════════════════════════════╗
║                    Telegram Webhook Started                        ║
╠════════════════════════════════════════════════════════════════════╣
║  URL:        https://{config.webhook.host}/{config.webhook.path:<35}║
║  Local:      http://{config.webhook.host}:{config.webhook.port:<37}║
╚════════════════════════════════════════════════════════════════════╝
    """)
    
    uvicorn.run(
        app,
        host=config.webhook.host,
        port=config.webhook.port,
        log_level=config.logging.level.lower(),
    )


if __name__ == "__main__":
    run_webhook()
