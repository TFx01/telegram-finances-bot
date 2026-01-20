#!/usr/bin/env python3
"""
Wrapper Server - FastAPI Application

Exposes REST endpoints for Telegram bot to interact with OpenCode.
This server acts as a bridge between Telegram and OpenCode's native REST API.

Usage:
    python wrapper_server.py

Endpoints:
    GET  /health              - Health check
    POST /session/start       - Create new session
    POST /session/:id/message - Send message to session
    GET  /session/:id/status  - Get session status
    GET  /agents              - List available agents
    DELETE /session/:id       - Delete session
    POST  /session/:id/abort  - Abort running session
"""

import asyncio
import json
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import AsyncGenerator, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from loguru import logger
from pydantic import BaseModel

from .config import get_config
from .opencode_client import (
    OpenCodeAPIError,
    OpenCodeClient,
    get_opencode_client,
    reset_opencode_client,
)
from .opencode_launcher import get_launcher, reset_launcher
from .sse_client import get_sse_client, EventType


# Configure logging
def setup_logging():
    """Configure loguru logger with file and console output"""
    config = get_config()

    logger.remove()

    log_dir = Path(__file__).parent.parent / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    # Console output with colors
    logger.add(
        lambda msg: print(msg, end=""),
        format=config.logging.format,
        level=config.logging.level,
        colorize=True,
    )

    # Rotating file log
    log_file = log_dir / "wrapper_{time:YYYY-MM-DD}.log"
    logger.add(
        str(log_file),
        format="[{time:YYYY-MM-DD HH:mm:ss}] {level}: {message}",
        level="DEBUG",
        rotation="1 day",
        retention="7 days",
        compression="gz",
        encoding="utf-8",
    )

    # Error-only log file
    error_log_file = log_dir / "errors_{time:YYYY-MM-DD}.log"
    logger.add(
        str(error_log_file),
        format="[{time:YYYY-MM-DD HH:mm:ss}] {level}: {message}",
        level="ERROR",
        rotation="1 day",
        retention="30 days",
        compression="gz",
        encoding="utf-8",
    )

    logger.info("Logging configured successfully")


setup_logging()


# Lifespan context manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    # Startup
    logger.info("Starting Wrapper Server...")

    config = get_config()
    launcher_config = config.opencode_launcher
    launcher = None
    opencode_started_by_us = False

    # Auto-start OpenCode if launcher is enabled
    if launcher_config.enabled:
        logger.info("OpenCode launcher enabled - checking OpenCode server...")
        launcher = get_launcher(
            host=launcher_config.host,
            port=launcher_config.port,
            password=launcher_config.password,
            opencode_path=launcher_config.opencode_path or None,
        )

        # Check if already running
        if launcher.is_running():
            logger.info("OpenCode server already running")
            # Verify it's healthy
            if await launcher.health_check(timeout=5.0):
                logger.success("OpenCode server is healthy")
            else:
                error_msg = "OpenCode server is running but health check failed"
                logger.critical(error_msg)
                if launcher_config.strict:
                    raise RuntimeError(error_msg)
                logger.warning("Starting anyway (non-strict mode)")
        else:
            # Need to start OpenCode
            logger.info("OpenCode server not running - starting...")
            try:
                started = await launcher.start(
                    wait_for_healthy=launcher_config.wait_for_healthy,
                    timeout=launcher_config.startup_timeout,
                    strict=launcher_config.strict,
                )
                if started:
                    logger.success("OpenCode server started automatically")
                    opencode_started_by_us = True
                else:
                    error_msg = "Failed to start OpenCode server"
                    logger.critical(error_msg)
                    if launcher_config.strict:
                        raise RuntimeError(error_msg)
                    logger.warning("Starting anyway (non-strict mode)")
            except RuntimeError as e:
                logger.critical(f"OpenCode startup failed: {e}")
                if launcher_config.strict:
                    raise
                logger.warning("Starting anyway (non-strict mode)")

    # Verify OpenCode connection
    client = get_opencode_client()
    try:
        health = await client.health_check()
        logger.success(f"OpenCode connected: {health}")
    except OpenCodeAPIError as e:
        logger.critical(f"OpenCode health check failed: {e.message}")
        if launcher_config.strict:
            raise RuntimeError(f"Cannot connect to OpenCode: {e.message}")
        logger.warning("Starting in degraded mode - OpenCode operations will fail")

    yield

    # Shutdown
    logger.info("Shutting down Wrapper Server...")

    # Stop all event consumers
    for session_id in list(_active_consumers.keys()):
        stop_event_consumer(session_id)

    reset_opencode_client()

    # Stop OpenCode if we started it
    if launcher_config.enabled and opencode_started_by_us:
        reset_launcher()
        logger.info("OpenCode server stopped")


# Create FastAPI app
config = get_config()
app = FastAPI(
    title="Wrapper Server - Telegram to OpenCode Bridge",
    description="REST API bridge between Telegram bot and OpenCode AI assistant",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors.origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Pydantic Models
# ============================================================================

class SessionStartRequest(BaseModel):
    """Request model for starting a new session"""
    chat_id: int
    title: Optional[str] = None
    agent: Optional[str] = None


class SessionStartResponse(BaseModel):
    """Response model for session start"""
    session_id: str
    status: str = "created"
    created_at: str


class MessageRequest(BaseModel):
    """Request model for sending a message"""
    chat_id: int
    message: str
    agent: Optional[str] = None
    model: Optional[dict] = None


class MessageResponse(BaseModel):
    """Response model for message send"""
    session_id: str
    status: str = "completed"
    response: str
    created_at: str


class AgentInfo(BaseModel):
    """Agent information model"""
    id: str
    name: str
    description: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    wrapper_version: str = "1.0.0"
    opencode_connected: bool
    timestamp: str


# ============================================================================
# Exception Handlers
# ============================================================================

@app.exception_handler(OpenCodeAPIError)
async def opencode_api_error_handler(request: Request, exc: OpenCodeAPIError):
    """Handle OpenCode API errors"""
    logger.error(f"OpenCode API Error: {exc.message}")
    return JSONResponse(
        status_code=exc.status_code or 500,
        content={
            "error": "OpenCode API Error",
            "message": exc.message,
            "status_code": exc.status_code,
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle any unexpected exceptions"""
    logger.exception(f"Unexpected error: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": str(exc) if app.debug else "An unexpected error occurred",
            "type": type(exc).__name__,
        },
    )


# ============================================================================
# Session Logging
# ============================================================================

# Ensure session_logs directory exists
SESSION_LOGS_DIR = Path(__file__).parent.parent / "session_logs"
SESSION_LOGS_DIR.mkdir(exist_ok=True)


def log_session_event(session_id: str, event: dict) -> None:
    """
    Append an event to the session's JSONL log file.

    Args:
        session_id: The OpenCode session ID
        event: The event dictionary to log
    """
    log_file = SESSION_LOGS_DIR / f"{session_id}.jsonl"

    # Add timestamp if not present
    if "timestamp" not in event:
        event["timestamp"] = datetime.now().isoformat()

    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
    except IOError as e:
        logger.error(f"Failed to log event for session {session_id}: {e}")


# ============================================================================
# Background Event Consumer
# ============================================================================

# Track active event consumers
_active_consumers: dict[str, asyncio.Task] = {}


async def consume_session_events(session_id: str) -> None:
    """
    Background task to consume SSE events for a session.

    Connects to OpenCode's global /event stream and logs all events
    for the specified session to the session_logs directory.

    Args:
        session_id: The OpenCode session ID to consume events for
    """
    logger.info(f"Starting background event consumer for session {session_id}")
    sse_client = get_sse_client()

    try:
        async for event in sse_client.stream_events(session_id):
            # Log the event to JSONL file
            log_session_event(session_id, event)
            logger.debug(f"Event logged for session {session_id}: {event.get('event', 'unknown')}")

    except asyncio.CancelledError:
        logger.info(f"Event consumer cancelled for session {session_id}")
    except Exception as e:
        logger.error(f"Event consumer error for session {session_id}: {e}")


def start_event_consumer(session_id: str) -> None:
    """
    Start a background event consumer for a session.

    Args:
        session_id: The OpenCode session ID
    """
    if session_id in _active_consumers:
        logger.warning(f"Event consumer already running for session {session_id}")
        return

    task = asyncio.create_task(consume_session_events(session_id))
    _active_consumers[session_id] = task
    logger.info(f"Event consumer started for session {session_id}")


def stop_event_consumer(session_id: str) -> None:
    """
    Stop the background event consumer for a session.

    Args:
        session_id: The OpenCode session ID
    """
    if session_id in _active_consumers:
        task = _active_consumers.pop(session_id)
        task.cancel()
        logger.info(f"Event consumer stopped for session {session_id}")


# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint.

    Verifies wrapper server is running and OpenCode is accessible.
    """
    client = get_opencode_client()
    opencode_healthy = False

    try:
        await client.health_check()
        opencode_healthy = True
    except OpenCodeAPIError:
        pass

    return HealthResponse(
        status="healthy" if opencode_healthy else "degraded",
        opencode_connected=opencode_healthy,
        timestamp=datetime.now().isoformat(),
    )


@app.get("/agents", response_model=list[AgentInfo])
async def list_agents():
    """
    List all available OpenCode agents.

    Returns a list of agents that can be used for task delegation.
    """
    client = get_opencode_client()
    agents = await client.list_agents()

    return [
        AgentInfo(
            id=agent.get("id", ""),
            name=agent.get("name", ""),
            description=agent.get("description"),
        )
        for agent in agents
    ]


@app.get("/session/{session_id}/events")
async def stream_session_events(session_id: str):
    """
    Stream SSE events from OpenCode for a session.

    Proxies events from OpenCode's /event endpoint and logs them to JSONL files.

    Args:
        session_id: The OpenCode session ID to stream events for

    Returns:
        StreamingResponse with text/event-stream content type
    """

    async def event_generator() -> AsyncGenerator[str, None]:
        """Generate SSE events for the client"""
        sse_client = get_sse_client()

        try:
            async for event in sse_client.stream_events(session_id):
                # Log the event to JSONL file
                log_session_event(session_id, event)

                # Format as SSE for client
                event_type = event.get("event", "message")
                event_data = event.get("data", event)

                if isinstance(event_data, dict):
                    event_data = json.dumps(event_data, ensure_ascii=False)

                yield f"event: {event_type}\ndata: {event_data}\n\n"

        except Exception as e:
            logger.error(f"SSE stream error for session {session_id}: {e}")
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

@app.post("/session/start", response_model=SessionStartResponse)
async def start_session(request: SessionStartRequest):
    """
    Create a new OpenCode session.

    Starts a background event consumer to log all SSE events for this session.

    Args:
        request: SessionStartRequest with chat_id and optional title/agent

    Returns:
        SessionStartResponse with session_id
    """
    client = get_opencode_client()

    # Build session title
    title = request.title or f"Telegram Chat {request.chat_id}"
    if request.agent:
        title = f"[{request.agent}] {title}"

    # Create session in OpenCode
    session_data = await client.create_session(title=title)
    session_id = session_data.get("id")

    if not session_id:
        raise HTTPException(
            status_code=500,
            detail="Failed to create session: no session ID returned",
        )

    # Start background event consumer for this session (if SSE is enabled)
    config = get_config()
    if config.sse.enabled:
        start_event_consumer(session_id)
    else:
        logger.info(f"SSE disabled - not starting event consumer for session {session_id}")

    logger.info(f"Session started: {session_id} for chat {request.chat_id}")

    return SessionStartResponse(
        session_id=session_id,
        status="created",
        created_at=datetime.now().isoformat(),
    )


@app.post("/session/{session_id}/message", response_model=MessageResponse)
async def send_message(session_id: str, request: MessageRequest):
    """
    Send a message to an existing session.

    Args:
        session_id: The OpenCode session ID
        request: MessageRequest with chat_id and message text

    Returns:
        MessageResponse with agent's response
    """
    client = get_opencode_client()
    config = get_config()

    # Verify session exists
    try:
        await client.get_session(session_id)
    except OpenCodeAPIError:
        raise HTTPException(
            status_code=404,
            detail=f"Session {session_id} not found",
        )

    # Use default agent from config if not specified
    agent = request.agent or config.session.default_agent or None

    # Send message to OpenCode
    result = await client.send_message(
        session_id=session_id,
        message=request.message,
        agent=agent,
        model=request.model,
    )

    # Extract response text from parts
    info = result.get("info", {})
    parts = result.get("parts", [])

    response_text = ""
    if isinstance(parts, list):
        for part in parts:
            # Ensure part is a dict before calling .get()
            if isinstance(part, dict):
                if part.get("type") == "text":
                    response_text = part.get("text", "")
                    break

    # Fallback to empty string if no text found
    if not response_text and parts:
        try:
            response_text = str(parts)
        except Exception:
            response_text = ""

    logger.info(f"Message sent to session {session_id}, response length: {len(response_text)}")

    return MessageResponse(
        session_id=session_id,
        status="completed",
        response=response_text,
        created_at=datetime.now().isoformat(),
    )


@app.get("/session/{session_id}/status")
async def get_session_status(session_id: str):
    """
    Get the status of a specific session.

    Returns session details and current state.
    """
    client = get_opencode_client()

    try:
        session = await client.get_session(session_id)
        return session
    except OpenCodeAPIError as e:
        raise HTTPException(
            status_code=404,
            detail=f"Session {session_id} not found: {e.message}",
        )


@app.delete("/session/{session_id}")
async def delete_session(session_id: str):
    """
    Delete a session, stop its event consumer, and all its data.

    Returns confirmation of deletion.
    """
    client = get_opencode_client()

    try:
        success = await client.delete_session(session_id)
        if success:
            # Stop the event consumer for this session
            stop_event_consumer(session_id)
            logger.info(f"Session deleted: {session_id}")
            return {"status": "deleted", "session_id": session_id}
        else:
            raise HTTPException(
                status_code=500,
                detail="Failed to delete session",
            )
    except OpenCodeAPIError as e:
        raise HTTPException(
            status_code=404,
            detail=f"Session not found: {e.message}",
        )


@app.post("/session/{session_id}/abort")
async def abort_session(session_id: str):
    """
    Abort a running session.

    Returns confirmation of abort.
    """
    client = get_opencode_client()

    try:
        success = await client.abort_session(session_id)
        if success:
            logger.info(f"Session aborted: {session_id}")
            return {"status": "aborted", "session_id": session_id}
        else:
            raise HTTPException(
                status_code=500,
                detail="Failed to abort session",
            )
    except OpenCodeAPIError as e:
        raise HTTPException(
            status_code=404,
            detail=f"Session not found: {e.message}",
        )


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    config = get_config()

    print(f"""
╔════════════════════════════════════════════════════════════════════╗
║                     Wrapper Server Started                         ║
╠════════════════════════════════════════════════════════════════════╣
║  URL:        http://{config.server.host}:{config.server.port}                        ║
║  OpenCode:   http://{config.opencode.host}:{config.opencode.port}                       ║
║                                                                ║
║  Endpoints:                                                  ║
║    GET  /health           - Health check                       ║
║    GET  /agents           - List agents                        ║
║    POST /session/start    - Create session                     ║
║    POST /session/:id/message - Send message                    ║
║    GET  /session/:id/status - Get session status               ║
║    DELETE /session/:id    - Delete session                     ║
║    POST /session/:id/abort - Abort session                     ║
╚════════════════════════════════════════════════════════════════════╝
    """)

    uvicorn.run(
        app,
        host=config.server.host,
        port=config.server.port,
        log_level=config.logging.level.lower(),
    )
