"""
Event Handler Module

Handles SSE events from the Wrapper Server and updates Telegram messages in real-time.
Provides progress indicators for agent delegations and completions.
"""

import asyncio
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional

from loguru import logger
from telegram import Bot


@dataclass
class EventProgress:
    """Tracks progress state for a message"""
    message_id: int
    chat_id: int
    created_at: datetime
    last_update: datetime
    agent: Optional[str] = None
    status: str = "processing"
    tool_in_progress: Optional[str] = None

    def elapsed_seconds(self) -> float:
        """Get seconds since event started"""
        return (datetime.now() - self.created_at).total_seconds()


class EventHandler:
    """
    Handles SSE events and updates Telegram messages.

    Provides real-time progress updates to users by editing
    the status message as events arrive.
    """

    # Status emoji mapping
    STATUS_EMOJI = {
        "processing": "⏳",
        "thinking": "🤔",
        "delegating": "🔄",
        "tool": "🔧",
        "complete": "✅",
        "error": "❌",
    }

    # Event type to status mapping
    EVENT_STATUS_MAP = {
        "message.start": "thinking",
        "message.part": "thinking",
        "message.complete": "complete",
        "agent.delegate": "delegating",
        "agent.complete": "complete",
        "tool.start": "tool",
        "tool.complete": "processing",
        "error": "error",
    }

    def __init__(self, bot: Bot, min_update_interval: float = 1.0):
        """
        Initialize the event handler.

        Args:
            bot: The Telegram Bot instance
            min_update_interval: Minimum seconds between message updates
                                 to avoid rate limiting
        """
        self.bot = bot
        self.min_update_interval = min_update_interval
        self._progress_states: Dict[int, EventProgress] = {}

    def create_progress(
        self,
        message_id: int,
        chat_id: int,
        agent: str = None,
    ) -> EventProgress:
        """Create a new progress tracker for a message"""
        progress = EventProgress(
            message_id=message_id,
            chat_id=chat_id,
            created_at=datetime.now(),
            last_update=datetime.now(),
            agent=agent,
        )
        self._progress_states[message_id] = progress
        return progress

    def get_progress(self, message_id: int) -> Optional[EventProgress]:
        """Get progress tracker for a message"""
        return self._progress_states.get(message_id)

    def remove_progress(self, message_id: int) -> None:
        """Remove progress tracker"""
        self._progress_states.pop(message_id, None)

    async def handle_event(
        self,
        event: Dict[str, Any],
        message_id: int,
        chat_id: int,
    ) -> Optional[str]:
        """
        Handle an SSE event and update Telegram message if needed.

        Args:
            event: The event dictionary from SSE stream
            message_id: The Telegram message ID to update
            chat_id: The Telegram chat ID

        Returns:
            Final response text if event is complete, None otherwise
        """
        progress = self.get_progress(message_id)
        if not progress:
            progress = self.create_progress(message_id, chat_id)

        event_type = event.get("event", "message")
        event_data = event.get("data", {})

        if isinstance(event_data, str):
            try:
                event_data = json.loads(event_data)
            except json.JSONDecodeError:
                event_data = {"text": event_data}

        # Update progress status based on event type
        new_status = self.EVENT_STATUS_MAP.get(event_type, progress.status)

        # Extract relevant information from event
        if event_type == "agent.delegate":
            progress.agent = event_data.get("agent", progress.agent)
            progress.status = "delegating"

        elif event_type == "tool.start":
            progress.tool_in_progress = event_data.get("tool", "unknown")
            progress.status = "tool"

        elif event_type == "tool.complete":
            progress.tool_in_progress = None
            progress.status = "processing"

        elif event_type == "message.complete" or event_type == "agent.complete":
            progress.status = "complete"
            self.remove_progress(message_id)

            # Extract the response text
            parts = event_data.get("parts", [])
            for part in parts:
                if part.get("type") == "text":
                    return part.get("text", "")

            return event_data.get("text", "")

        elif event_type == "error":
            progress.status = "error"
            self.remove_progress(message_id)
            return f"❌ Error: {event_data.get('message', 'Unknown error')}"

        else:
            progress.status = new_status

        # Rate limit message updates
        seconds_since_update = (datetime.now() - progress.last_update).total_seconds()
        if seconds_since_update >= self.min_update_interval:
            await self._update_message(progress)
            progress.last_update = datetime.now()

        return None

    async def _update_message(self, progress: EventProgress) -> None:
        """Update the Telegram message with current progress"""
        emoji = self.STATUS_EMOJI.get(progress.status, "⏳")
        elapsed = int(progress.elapsed_seconds())

        status_text = self._build_status_text(progress)

        message_text = f"{emoji} {status_text}\n\n⏱️ {elapsed}s"

        try:
            await self.bot.edit_message_text(
                chat_id=progress.chat_id,
                message_id=progress.message_id,
                text=message_text,
            )
        except Exception as e:
            # Ignore edit errors (message may be unchanged, deleted, etc.)
            logger.debug(f"Failed to update message {progress.message_id}: {e}")

    def _build_status_text(self, progress: EventProgress) -> str:
        """Build human-readable status text"""
        if progress.status == "thinking":
            return "Thinking..."

        elif progress.status == "delegating":
            agent_name = progress.agent or "agent"
            return f"Delegating to {agent_name}..."

        elif progress.status == "tool":
            tool_name = progress.tool_in_progress or "tool"
            return f"Using {tool_name}..."

        elif progress.status == "processing":
            return "Processing..."

        elif progress.status == "complete":
            return "Complete!"

        elif progress.status == "error":
            return "Error occurred"

        return "Working..."


# Global event handler instance (initialized with bot)
_event_handler: Optional[EventHandler] = None


def get_event_handler(bot: Bot = None) -> EventHandler:
    """
    Get global event handler instance.

    Args:
        bot: The Telegram Bot instance (required on first call)

    Returns:
        The EventHandler instance
    """
    global _event_handler
    if _event_handler is None:
        if bot is None:
            raise ValueError("Bot instance required to initialize event handler")
        _event_handler = EventHandler(bot)
    return _event_handler


def reset_event_handler() -> None:
    """Reset global event handler (useful for testing)"""
    global _event_handler
    _event_handler = None
