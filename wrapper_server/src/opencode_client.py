"""
OpenCode REST API Client

Interacts with OpenCode's native REST API to create sessions,
send messages, and manage agent interactions.
"""

import base64
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
from loguru import logger

from .config import get_config


class OpenCodeAPIError(Exception):
    """Exception raised when OpenCode API returns an error"""

    def __init__(self, message: str, status_code: int = None, response_body: str = None):
        self.message = message
        self.status_code = status_code
        self.response_body = response_body
        super().__init__(self.message)


class OpenCodeClient:
    """HTTP client for OpenCode REST API"""

    def __init__(
        self,
        host: str = None,
        port: int = None,
        username: str = None,
        password: str = None,
        timeout: float = None
    ):
        config = get_config()

        self.host = host or config.opencode.host
        self.port = port or config.opencode.port
        self.username = username or config.opencode.username
        self.password = password or config.opencode.password
        self.timeout = timeout or config.request.timeout

        self.base_url = f"http://{self.host}:{self.port}"
        self.http_client = httpx.AsyncClient(timeout=self.timeout)

        logger.info(f"OpenCode client initialized: {self.base_url}")

    def _get_auth_header(self) -> Dict[str, str]:
        """Generate HTTP Basic Auth header"""
        if not self.password:
            return {}

        credentials = f"{self.username}:{self.password}"
        encoded = base64.b64encode(credentials.encode()).decode()
        return {"Authorization": f"Basic {encoded}"}

    async def health_check(self) -> Dict[str, Any]:
        """Check OpenCode server health"""
        # Try multiple endpoints - OpenCode may return HTML for unknown endpoints
        endpoints = [
            "/global/health",
            "/session",  # Fallback: session list should always work
        ]

        for endpoint in endpoints:
            try:
                response = await self.http_client.get(
                    f"{self.base_url}{endpoint}",
                    headers=self._get_auth_header()
                )
                response.raise_for_status()

                # Handle empty or non-JSON responses
                if not response.content:
                    logger.debug(f"Health check ({endpoint}) returned empty response")
                    continue

                try:
                    data = response.json()
                    logger.debug(f"Health check ({endpoint}) succeeded")
                    return data
                except json.JSONDecodeError:
                    logger.warning(f"Health check ({endpoint}) returned non-JSON response: {response.text[:100]}...")
                    continue

            except httpx.HTTPError as e:
                logger.info(f"Health check ({endpoint}) failed: {e}")
                continue

        # All endpoints failed, return a basic healthy response
        logger.warning("All health check endpoints failed, assuming server is running")
        return {"status": "healthy", "message": "server responded but health endpoint unavailable"}

    async def list_agents(self) -> List[Dict[str, Any]]:
        """List all available agents"""
        try:
            response = await self.http_client.get(
                f"{self.base_url}/agent",
                headers=self._get_auth_header()
            )
            response.raise_for_status()
            data = response.json()
            # Handle both dict with "data" key and direct list response
            if isinstance(data, list):
                return data
            elif isinstance(data, dict):
                return data.get("data", [])
            else:
                logger.warning(f"Unexpected agents response type: {type(data)}")
                return []
        except httpx.HTTPError as e:
            logger.error(f"Failed to list agents: {e}")
            raise OpenCodeAPIError(f"Failed to list agents: {str(e)}")

    async def create_session(
        self,
        title: str = None,
        parent_id: str = None
    ) -> Dict[str, Any]:
        """Create a new session"""
        try:
            body = {}
            if title:
                body["title"] = title
            if parent_id:
                body["parentID"] = parent_id

            response = await self.http_client.post(
                f"{self.base_url}/session",
                json=body,
                headers=self._get_auth_header()
            )
            response.raise_for_status()
            data = response.json()
            logger.success(f"Session created: {data.get('id')}")
            return data
        except httpx.HTTPError as e:
            logger.error(f"Failed to create session: {e}")
            raise OpenCodeAPIError(f"Failed to create session: {str(e)}")

    async def get_session(self, session_id: str) -> Dict[str, Any]:
        """Get session details"""
        try:
            response = await self.http_client.get(
                f"{self.base_url}/session/{session_id}",
                headers=self._get_auth_header()
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Failed to get session {session_id}: {e}")
            raise OpenCodeAPIError(f"Failed to get session: {str(e)}")

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session"""
        try:
            response = await self.http_client.delete(
                f"{self.base_url}/session/{session_id}",
                headers=self._get_auth_header()
            )
            response.raise_for_status()
            logger.info(f"Session deleted: {session_id}")
            return True
        except httpx.HTTPError as e:
            logger.error(f"Failed to delete session {session_id}: {e}")
            raise OpenCodeAPIError(f"Failed to delete session: {str(e)}")

    async def send_message(
        self,
        session_id: str,
        message: str,
        agent: str = None,
        model: Dict[str, str] = None,
        message_id: str = None
    ) -> Dict[str, Any]:
        """
        Send a message to a session and wait for response.

        Args:
            session_id: The session ID
            message: The message text
            agent: Optional agent ID to use
            model: Optional model specification {"providerID": "...", "modelID": "..."}
            message_id: Optional message ID for continuation

        Returns:
            Dict with 'info' (message info) and 'parts' (response parts)
        """
        try:
            body: Dict[str, Any] = {
                "parts": [{"type": "text", "text": message}]
            }

            if message_id:
                body["messageID"] = message_id
            if agent:
                body["agent"] = agent
            if model:
                body["model"] = model

            # Ensure client is healthy before making request
            await self.ensure_healthy()
            
            response = await self.http_client.post(
                f"{self.base_url}/session/{session_id}/message",
                json=body,
                headers=self._get_auth_header()
            )
            
            # Log response details for debugging
            logger.debug(f"Response status: {response.status_code}")
            logger.debug(f"Response headers: {dict(response.headers)}")
            logger.debug(f"Response content length: {len(response.content)}")
            
            response.raise_for_status()

            # Check if response is empty
            if not response.content:
                logger.error(f"Empty response from OpenCode for session {session_id}")
                raise OpenCodeAPIError("Empty response from OpenCode")

            try:
                data = response.json()
                logger.debug(f"Message sent to session {session_id}")
                return data
            except Exception as e:
                logger.error(f"Failed to parse JSON response: {e}")
                logger.error(f"Response text (first 500 chars): {response.text[:500] if response.text else 'EMPTY'}")
                raise OpenCodeAPIError(f"Invalid JSON response from OpenCode: {str(e)}")
        except httpx.HTTPError as e:
            logger.error(f"Failed to send message to session {session_id}: {e}")
            raise OpenCodeAPIError(f"Failed to send message: {str(e)}")

    async def send_message_async(
        self,
        session_id: str,
        message: str,
        agent: str = None,
        model: Dict[str, str] = None
    ) -> bool:
        """
        Send a message asynchronously (no wait for response).

        Returns:
            True if request was accepted
        """
        try:
            body: Dict[str, Any] = {
                "parts": [{"type": "text", "text": message}]
            }

            if agent:
                body["agent"] = agent
            if model:
                body["model"] = model

            response = await self.http_client.post(
                f"{self.base_url}/session/{session_id}/prompt_async",
                json=body,
                headers=self._get_auth_header()
            )
            response.raise_for_status()

            # Async endpoint returns 204 No Content on success
            return response.status_code == 204
        except httpx.HTTPError as e:
            logger.error(f"Failed to send async message to session {session_id}: {e}")
            raise OpenCodeAPIError(f"Failed to send async message: {str(e)}")

    async def abort_session(self, session_id: str) -> bool:
        """Abort a running session"""
        try:
            response = await self.http_client.post(
                f"{self.base_url}/session/{session_id}/abort",
                headers=self._get_auth_header()
            )
            response.raise_for_status()
            logger.info(f"Session aborted: {session_id}")
            return True
        except httpx.HTTPError as e:
            logger.error(f"Failed to abort session {session_id}: {e}")
            raise OpenCodeAPIError(f"Failed to abort session: {str(e)}")

    async def get_messages(self, session_id: str, limit: int = None) -> List[Dict[str, Any]]:
        """Get messages in a session"""
        try:
            params = {}
            if limit:
                params["limit"] = limit

            response = await self.http_client.get(
                f"{self.base_url}/session/{session_id}/message",
                params=params,
                headers=self._get_auth_header()
            )
            response.raise_for_status()

            data = response.json()
            return data.get("data", [])
        except httpx.HTTPError as e:
            logger.error(f"Failed to get messages for session {session_id}: {e}")
            raise OpenCodeAPIError(f"Failed to get messages: {str(e)}")

    async def get_session_status(self) -> Dict[str, Any]:
        """Get status of all sessions"""
        try:
            response = await self.http_client.get(
                f"{self.base_url}/session/status",
                headers=self._get_auth_header()
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Failed to get session status: {e}")
            raise OpenCodeAPIError(f"Failed to get session status: {str(e)}")

    async def close(self) -> None:
        """Close the HTTP client"""
        await self.http_client.aclose()
        logger.debug("OpenCode HTTP client closed")

    async def is_healthy(self) -> bool:
        """Check if the client is still healthy and responsive"""
        try:
            response = await self.http_client.get(
                f"{self.base_url}/global/health",
                headers=self._get_auth_header(),
                timeout=5.0
            )
            return response.status_code == 200
        except Exception:
            return False

    async def ensure_healthy(self) -> None:
        """Ensure client is healthy, recreate if needed"""
        if not await self.is_healthy():
            logger.warning("OpenCode client is unhealthy, recreating...")
            await self.close()
            self.http_client = httpx.AsyncClient(timeout=self.timeout)
            logger.info("OpenCode client recreated")


# Global client instance
_client: Optional[OpenCodeClient] = None


def get_opencode_client() -> OpenCodeClient:
    """Get global OpenCode client instance"""
    global _client
    if _client is None:
        _client = OpenCodeClient()
    return _client


def reset_opencode_client() -> None:
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
