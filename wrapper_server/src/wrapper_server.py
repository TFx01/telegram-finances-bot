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
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger
from pydantic import BaseModel

from .config import get_config
from .opencode_client import (
    OpenCodeAPIError,
    OpenCodeClient,
    get_opencode_client,
    reset_opencode_client,
)


# Configure logging
def setup_logging():
    """Configure loguru logger"""
    config = get_config()
    logger.remove()
    logger.add(
        lambda msg: print(msg, end=""),
        format=config.logging.format,
        level=config.logging.level,
        colorize=True,
    )


setup_logging()


# Lifespan context manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    # Startup
    logger.info("Starting Wrapper Server...")
    client = get_opencode_client()
    
    # Verify OpenCode connection
    try:
        health = await client.health_check()
        logger.success(f"OpenCode connected: {health}")
    except OpenCodeAPIError as e:
        logger.warning(f"OpenCode health check failed: {e.message}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Wrapper Server...")
    reset_opencode_client()


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


@app.post("/session/start", response_model=SessionStartResponse)
async def start_session(request: SessionStartRequest):
    """
    Create a new OpenCode session.
    
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
    
    # Verify session exists
    try:
        await client.get_session(session_id)
    except OpenCodeAPIError:
        raise HTTPException(
            status_code=404,
            detail=f"Session {session_id} not found",
        )
    
    # Send message to OpenCode
    result = await client.send_message(
        session_id=session_id,
        message=request.message,
        agent=request.agent,
        model=request.model,
    )
    
    # Extract response text from parts
    info = result.get("info", {})
    parts = result.get("parts", [])
    
    response_text = ""
    for part in parts:
        if part.get("type") == "text":
            response_text = part.get("text", "")
            break
    
    # Fallback to empty string if no text found
    if not response_text and parts:
        response_text = str(parts)
    
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
    Delete a session and all its data.
    
    Returns confirmation of deletion.
    """
    client = get_opencode_client()
    
    try:
        success = await client.delete_session(session_id)
        if success:
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
