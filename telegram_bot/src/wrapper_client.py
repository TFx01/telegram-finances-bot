"""
Wrapper Client Module

HTTP client for communicating with the Wrapper Server.
"""

import sys
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, Optional

import httpx

# Ensure src is in path for imports
_src_path = Path(__file__).parent
if str(_src_path) not in sys.path:
    sys.path.insert(0, str(_src_path.parent))

from loguru import logger

from config import get_config


class WrapperAPIError(Exception):
    """Exception raised when Wrapper Server returns an error"""

    def __init__(self, message: str, status_code: int = None, response_body: str = None):
        self.message = message
        self.status_code = status_code
        self.response_body = response_body
        super().__init__(self.message)


class WrapperClient:
    """HTTP client for Wrapper Server"""

    def __init__(self, url: str = None, timeout: int = None):
        config = get_config()

        self.url = url or config.wrapper.url
        self.timeout = timeout or config.wrapper.timeout

        self.http_client = httpx.AsyncClient(timeout=self.timeout)
        logger.debug(f"Wrapper client initialized: {self.url}")

    async def close(self) -> None:
        """Close the HTTP client"""
        await self.http_client.aclose()

    async def health_check(self) -> Dict[str, Any]:
        """Check wrapper server health"""
        try:
            response = await self.http_client.get(f"{self.url}/health")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Health check failed: {e}")
            raise WrapperAPIError(f"Health check failed: {str(e)}")

    async def start_session(
        self,
        chat_id: int,
        title: str = None,
        agent: str = None,
    ) -> Dict[str, Any]:
        """Start a new session"""
        try:
            response = await self.http_client.post(
                f"{self.url}/session/start",
                json={
                    "chat_id": chat_id,
                    "title": title,
                    "agent": agent,
                },
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Failed to start session: {e}")
            raise WrapperAPIError(f"Failed to start session: {str(e)}")

    async def send_message(
        self,
        session_id: str,
        message: str,
        chat_id: int = None,
        agent: str = None,
        model: Dict[str, str] = None,
    ) -> Dict[str, Any]:
        """Send a message to a session"""
        try:
            response = await self.http_client.post(
                f"{self.url}/session/{session_id}/message",
                json={
                    "chat_id": chat_id,
                    "message": message,
                    "agent": agent,
                    "model": model,
                },
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Failed to send message: {e}")
            raise WrapperAPIError(f"Failed to send message: {str(e)}")

    async def send_audio(
        self,
        session_id: str,
        audio_path: str,
        chat_id: int = None,
    ) -> Dict[str, Any]:
        """Send an audio file for transcription/processing"""
        try:
            with open(audio_path, "rb") as audio_file:
                response = await self.http_client.post(
                    f"{self.url}/session/{session_id}/audio",
                    files={"audio": audio_file},
                    data={"chat_id": str(chat_id) if chat_id else None},
                )
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPError, IOError) as e:
            logger.error(f"Failed to send audio: {e}")
            raise WrapperAPIError(f"Failed to send audio: {str(e)}")

    async def send_image(
        self,
        session_id: str,
        image_path: str,
        chat_id: int = None,
    ) -> Dict[str, Any]:
        """Send an image for analysis"""
        try:
            with open(image_path, "rb") as image_file:
                response = await self.http_client.post(
                    f"{self.url}/session/{session_id}/image",
                    files={"image": image_file},
                    data={"chat_id": str(chat_id) if chat_id else None},
                )
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPError, IOError) as e:
            logger.error(f"Failed to send image: {e}")
            raise WrapperAPIError(f"Failed to send image: {str(e)}")

    async def get_session_status(self, session_id: str) -> Dict[str, Any]:
        """Get session status"""
        try:
            response = await self.http_client.get(
                f"{self.url}/session/{session_id}/status"
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Failed to get session status: {e}")
            raise WrapperAPIError(f"Failed to get session status: {str(e)}")

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session"""
        try:
            response = await self.http_client.delete(
                f"{self.url}/session/{session_id}"
            )
            response.raise_for_status()
            return True
        except httpx.HTTPError as e:
            logger.error(f"Failed to delete session: {e}")
            raise WrapperAPIError(f"Failed to delete session: {str(e)}")

    async def abort_session(self, session_id: str) -> bool:
        """Abort a running session"""
        try:
            response = await self.http_client.post(
                f"{self.url}/session/{session_id}/abort"
            )
            response.raise_for_status()
            return True
        except httpx.HTTPError as e:
            logger.error(f"Failed to abort session: {e}")
            raise WrapperAPIError(f"Failed to abort session: {str(e)}")

    async def list_agents(self) -> list[Dict[str, Any]]:
        """List available agents"""
        try:
            response = await self.http_client.get(f"{self.url}/agents")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Failed to list agents: {e}")
            raise WrapperAPIError(f"Failed to list agents: {str(e)}")

    async def stream_events(
        self,
        session_id: str,
    ) -> "AsyncGenerator[Dict[str, Any], None]":
        """
        Stream SSE events from the wrapper server for a session.

        Yields parsed event dictionaries as they arrive.

        Args:
            session_id: The OpenCode session ID to stream events for

        Yields:
            Dict with event data
        """
        import json as json_module

        url = f"{self.url}/session/{session_id}/events"

        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream(
                "GET",
                url,
                headers={"Accept": "text/event-stream"},
            ) as response:
                response.raise_for_status()

                current_event: Dict[str, Any] = {}

                async for line in response.aiter_lines():
                    line = line.strip()

                    if not line:
                        # Empty line = end of event
                        if current_event:
                            # Parse data field as JSON if present
                            if "data" in current_event:
                                try:
                                    current_event["data"] = json_module.loads(current_event["data"])
                                except json_module.JSONDecodeError:
                                    pass
                            yield current_event
                            current_event = {}
                        continue

                    if line.startswith(":"):
                        # Comment line, skip
                        continue

                    # Parse field: value
                    if ":" in line:
                        field, _, value = line.partition(":")
                        value = value.lstrip()

                        if field == "data":
                            if "data" in current_event:
                                current_event["data"] += "\n" + value
                            else:
                                current_event["data"] = value
                        else:
                            current_event[field] = value
                    else:
                        current_event[line] = ""

                # Yield any remaining event
                if current_event:
                    if "data" in current_event:
                        try:
                            current_event["data"] = json_module.loads(current_event["data"])
                        except json_module.JSONDecodeError:
                            pass
                    yield current_event


# Global client instance
_client: Optional[WrapperClient] = None


def get_wrapper_client() -> WrapperClient:
    """Get global wrapper client instance"""
    global _client
    if _client is None:
        _client = WrapperClient()
    return _client


def reset_wrapper_client() -> None:
    """Reset global client (useful for testing)"""
    global _client
    if _client:
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(_client.close())
            else:
                loop.run_until_complete(_client.close())
        except RuntimeError:
            pass
    _client = None
