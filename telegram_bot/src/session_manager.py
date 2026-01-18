"""
Session Manager Module

Manages Telegram chat sessions and their corresponding OpenCode session IDs.
Provides persistent storage for session mappings.
"""

import sys
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

# Ensure src is in path for imports
_src_path = Path(__file__).parent
if str(_src_path) not in sys.path:
    sys.path.insert(0, str(_src_path.parent))

from loguru import logger

from config import get_config


class SessionData:
    """Session data structure"""
    
    def __init__(
        self,
        chat_id: int,
        opencode_session_id: str = None,
        created_at: datetime = None,
        last_activity: datetime = None,
        is_active: bool = True,
        agent: str = None,
        model: Dict[str, str] = None,
    ):
        self.chat_id = chat_id
        self.opencode_session_id = opencode_session_id
        self.created_at = created_at or datetime.now()
        self.last_activity = last_activity or datetime.now()
        self.is_active = is_active
        self.agent = agent
        self.model = model
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            "chat_id": self.chat_id,
            "opencode_session_id": self.opencode_session_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_activity": self.last_activity.isoformat() if self.last_activity else None,
            "is_active": self.is_active,
            "agent": self.agent,
            "model": self.model,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SessionData":
        """Create from dictionary"""
        created_at = None
        last_activity = None
        
        if data.get("created_at"):
            created_at = datetime.fromisoformat(data["created_at"])
        if data.get("last_activity"):
            last_activity = datetime.fromisoformat(data["last_activity"])
        
        return cls(
            chat_id=data["chat_id"],
            opencode_session_id=data.get("opencode_session_id"),
            created_at=created_at,
            last_activity=last_activity,
            is_active=data.get("is_active", True),
            agent=data.get("agent"),
            model=data.get("model"),
        )


class SessionManager:
    """
    Manages session storage and retrieval.
    
    Supports memory-only storage (default) and file-based persistence.
    """
    
    def __init__(self, storage_path: str = None):
        config = get_config()
        
        # Determine storage type and path
        storage_type = config.session.storage
        self.storage_path = storage_path
        
        if storage_type == "file" and not storage_path:
            # Default to sessions.json in current directory
            self.storage_path = Path.cwd() / "sessions.json"
        elif storage_type == "memory":
            self.storage_path = None
        
        self._sessions: Dict[int, SessionData] = {}
        
        # Load existing sessions from file
        if self.storage_path and Path(self.storage_path).exists():
            self._load_sessions()
        
        logger.info(f"Session manager initialized (storage: {storage_type})")
    
    def _load_sessions(self):
        """Load sessions from file"""
        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                for chat_id, session_data in data.items():
                    self._sessions[int(chat_id)] = SessionData.from_dict(session_data)
            logger.info(f"Loaded {len(self._sessions)} sessions from file")
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Failed to load sessions: {e}")
    
    def _save_sessions(self):
        """Save sessions to file"""
        if not self.storage_path:
            return
        
        try:
            data = {
                str(chat_id): session.to_dict()
                for chat_id, session in self._sessions.items()
            }
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except IOError as e:
            logger.error(f"Failed to save sessions: {e}")
    
    def get_session(self, chat_id: int) -> Optional[SessionData]:
        """
        Get session for a chat ID.
        
        Returns None if no session exists.
        """
        return self._sessions.get(chat_id)
    
    def get_or_create(
        self,
        chat_id: int,
        opencode_session_id: str = None,
        agent: str = None,
        model: Dict[str, str] = None,
    ) -> SessionData:
        """
        Get existing session or create new one.
        
        If session exists but is inactive, it will be reactivated.
        """
        if chat_id in self._sessions:
            session = self._sessions[chat_id]
            # Reactivate if inactive
            if not session.is_active:
                session.is_active = True
                session.last_activity = datetime.now()
                logger.info(f"Reactivated session for chat {chat_id}")
            return session
        
        # Create new session
        session = SessionData(
            chat_id=chat_id,
            opencode_session_id=opencode_session_id,
            agent=agent,
            model=model,
        )
        self._sessions[chat_id] = session
        self._save_sessions()
        logger.info(f"Created new session for chat {chat_id}")
        return session
    
    def update_session(
        self,
        chat_id: int,
        opencode_session_id: str = None,
        agent: str = None,
        model: Dict[str, str] = None,
    ) -> bool:
        """
        Update session with new values.
        
        Returns True if session was updated, False if not found.
        """
        if chat_id not in self._sessions:
            return False
        
        session = self._sessions[chat_id]
        
        if opencode_session_id:
            session.opencode_session_id = opencode_session_id
        if agent:
            session.agent = agent
        if model:
            session.model = model
        
        session.last_activity = datetime.now()
        self._save_sessions()
        return True
    
    def set_active(self, chat_id: int, is_active: bool = True) -> bool:
        """Set session active status"""
        if chat_id not in self._sessions:
            return False
        
        self._sessions[chat_id].is_active = is_active
        self._sessions[chat_id].last_activity = datetime.now()
        self._save_sessions()
        return True
    
    def delete_session(self, chat_id: int) -> bool:
        """Delete a session"""
        if chat_id not in self._sessions:
            return False
        
        del self._sessions[chat_id]
        self._save_sessions()
        logger.info(f"Deleted session for chat {chat_id}")
        return True
    
    def list_sessions(self) -> list[SessionData]:
        """List all active sessions"""
        return [
            session
            for session in self._sessions.values()
            if session.is_active
        ]
    
    def cleanup_inactive(self, max_age_seconds: int = None) -> int:
        """
        Remove sessions that have been inactive for too long.
        
        Returns number of sessions removed.
        """
        if max_age_seconds is None:
            config = get_config()
            max_age_seconds = config.session.timeout
        
        cutoff = datetime.now()
        
        sessions_to_remove = []
        for chat_id, session in self._sessions.items():
            if (
                session.is_active
                and session.last_activity
                and (cutoff - session.last_activity).total_seconds() > max_age_seconds
            ):
                sessions_to_remove.append(chat_id)
        
        for chat_id in sessions_to_remove:
            self.delete_session(chat_id)
        
        if sessions_to_remove:
            logger.info(f"Cleaned up {len(sessions_to_remove)} inactive sessions")
        
        return len(sessions_to_remove)


# Global session manager instance
_session_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    """Get global session manager instance"""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager


def reset_session_manager() -> None:
    """Reset global session manager (useful for testing)"""
    global _session_manager
    _session_manager = None
