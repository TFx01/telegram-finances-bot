"""
SSE Client Module

Connects to OpenCode's Server-Sent Events endpoint to stream real-time events.
Handles reconnection and event parsing.
"""

import asyncio
import json
from typing import Any, AsyncGenerator, Dict, Optional

import httpx
from loguru import logger

from .config import get_config


class SSEClient:
    """
    SSE Client for streaming events from OpenCode.

    Connects to OpenCode's GET /event endpoint to receive real-time events
    about session activity, agent delegations, and completions.
    """

    def __init__(
        self,
        base_url: str = None,
        auth_header: Dict[str, str] = None,
        timeout: float = None,
    ):
        config = get_config()

        self.base_url = base_url or f"http://{config.opencode.host}:{config.opencode.port}"
        self.auth_header = auth_header or {}
        self.timeout = timeout or config.request.timeout

    async def stream_events(
        self,
        session_id: str = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream events from OpenCode's global /event endpoint.

        OpenCode's /event endpoint is a GLOBAL event stream - it sends events
        for ALL sessions. To get session-specific events, we filter by session_id.

        According to OpenCode docs:
        - Endpoint: GET /event (no sessionID parameter)
        - First event is "server.connected"
        - Then bus events for all sessions

        Args:
            session_id: Optional. If provided, only yield events for this session.
                       If None, yield all events.

        Yields:
            Dict with event data (type, data, id, etc.)
        """
        url = f"{self.base_url}/event"

        logger.debug(f"Connecting to SSE endpoint: {url}")

        async with httpx.AsyncClient(timeout=None) as client:
            try:
                async with client.stream(
                    "GET",
                    url,
                    headers={
                        **self.auth_header,
                        "Accept": "text/event-stream",
                        "Cache-Control": "no-cache",
                    },
                ) as response:
                    response.raise_for_status()
                    logger.info(f"SSE connection established (global stream)")

                    # Parse SSE stream with optional session filtering
                    async for event in self._parse_sse_stream(response, session_id):
                        yield event

            except httpx.HTTPStatusError as e:
                logger.error(f"SSE connection failed: {e}")
                raise
            except httpx.ReadTimeout:
                logger.warning("SSE connection timed out, will retry")
                raise
            except Exception as e:
                logger.error(f"SSE stream error: {e}")
                raise
            except httpx.ReadTimeout:
                logger.warning("SSE connection timed out, will retry")
                raise
            except Exception as e:
                logger.error(f"SSE stream error: {e}")
                raise

    async def _parse_sse_stream(
        self,
        response: httpx.Response,
        session_id: str = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Parse SSE text/event-stream format into events.

        SSE format:
            event: event_type
            data: {"json": "data"}
            id: event_id

            (blank line separates events)

        Args:
            response: The HTTP response object
            session_id: Optional session ID to filter events by.
                       If provided, only yield events matching this session.
        """
        current_event: Dict[str, Any] = {}

        async for line in response.aiter_lines():
            line = line.strip()

            if not line:
                # Empty line = end of event
                if current_event:
                    # Parse data field as JSON if present
                    if "data" in current_event:
                        try:
                            current_event["data"] = json.loads(current_event["data"])
                        except json.JSONDecodeError:
                            pass  # Keep as string

                    # Session filtering: check if event belongs to target session
                    if session_id:
                        if not self._event_matches_session(current_event, session_id):
                            # Skip this event - not for our session
                            current_event = {}
                            continue

                    logger.debug(f"SSE event received: {current_event.get('event', 'message')}")
                    yield current_event
                    current_event = {}
                continue

            if line.startswith(":"):
                # Comment line, skip
                continue

            # Parse field: value
            if ":" in line:
                field, _, value = line.partition(":")
                value = value.lstrip()  # Remove leading space

                if field == "data":
                    # Data can be multi-line, concatenate
                    if "data" in current_event:
                        current_event["data"] += "\n" + value
                    else:
                        current_event["data"] = value
                else:
                    current_event[field] = value
            else:
                # Field with no value
                current_event[line] = ""

        # Yield any remaining event
        if current_event:
            if "data" in current_event:
                try:
                    current_event["data"] = json.loads(current_event["data"])
                except json.JSONDecodeError:
                    pass

            # Session filtering for final event
            if session_id:
                if not self._event_matches_session(current_event, session_id):
                    return  # Skip - not for our session

            yield current_event

    def _event_matches_session(self, event: Dict[str, Any], session_id: str) -> bool:
        """
        Check if an event belongs to a specific session.

        OpenCode events can contain session_id in various places:
        - In the event data: event.data.sessionID, event.data.session_id
        - In the event type: "session.{session_id}.message.start"
        - Direct in the data dict

        Args:
            event: The parsed event dictionary
            session_id: The session ID to match against

        Returns:
            True if the event belongs to the session
        """
        event_type = event.get("event", "")
        event_data = event.get("data", {})

        # 1. Check if event type contains session_id (e.g., "session.abc123.message.start")
        if session_id in event_type:
            return True

        # 2. Check if data is a dict with sessionID/session_id
        if isinstance(event_data, dict):
            if event_data.get("sessionID") == session_id:
                return True
            if event_data.get("session_id") == session_id:
                return True

        # 3. Check data as string for session_id pattern
        if isinstance(event_data, str):
            if session_id in event_data:
                return True

        # 4. Check if this is a global event (no session filtering needed)
        if event_type in ("server.connected", "server.heartbeat", "heartbeat"):
            return True

        # Default: assume it's for our session if we can't determine otherwise
        # This is a fallback - in practice OpenCode should include session info
        return True


class EventType:
    """Known OpenCode event types from /event SSE endpoint"""
    SERVER_CONNECTED = "server.connected"
    MESSAGE_START = "message.start"
    MESSAGE_PART = "message.part"
    MESSAGE_COMPLETE = "message.complete"
    AGENT_DELEGATE = "agent.delegate"
    AGENT_COMPLETE = "agent.complete"
    TOOL_START = "tool.start"
    TOOL_COMPLETE = "tool.complete"
    ERROR = "error"


# Global SSE client instance
_sse_client: Optional[SSEClient] = None


def get_sse_client() -> SSEClient:
    """Get global SSE client instance"""
    global _sse_client
    if _sse_client is None:
        _sse_client = SSEClient()
    return _sse_client


def reset_sse_client() -> None:
    """Reset global SSE client (useful for testing)"""
    global _sse_client
    _sse_client = None
