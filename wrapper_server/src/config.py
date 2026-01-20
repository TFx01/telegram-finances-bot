"""
Wrapper Server Configuration Module

Loads configuration from:
1. .env file (for local development)
2. config.yaml (for project settings)
3. Environment variables (highest priority)
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field


class OpenCodeConfig(BaseModel):
    """OpenCode API configuration"""
    host: str = "127.0.0.1"
    port: int = 4096
    username: str = "opencode"
    password: str = ""


class OpenCodeLauncherConfig(BaseModel):
    """OpenCode server launcher configuration"""
    enabled: bool = False  # Set to True to auto-start OpenCode
    strict: bool = True  # If True, fail startup if OpenCode is unreachable
    opencode_path: str = ""  # Path to opencode binary (empty = auto-detect)
    host: str = "127.0.0.1"
    port: int = 4096
    password: str = ""
    wait_for_healthy: bool = True
    startup_timeout: float = 60.0  # seconds


class ServerConfig(BaseModel):
    """Server configuration"""
    host: str = "0.0.0.0"
    port: int = 5147


class CORSConfig(BaseModel):
    """CORS configuration"""
    origins: List[str] = Field(default_factory=lambda: [])


class LoggingConfig(BaseModel):
    """Logging configuration"""
    level: str = "INFO"
    format: str = "[{time}] {level}: {message}"


class SessionConfig(BaseModel):
    """Session configuration"""
    timeout: int = 300
    max_message_length: int = 4096
    default_agent: str = "finances-orchestrator"


class RequestConfig(BaseModel):
    """Request configuration"""
    timeout: float = 300.0


class SSEConfig(BaseModel):
    """SSE event configuration"""
    enabled: bool = False  # Set to True to enable SSE event consumption (memory intensive)
    log_dir: str = "session_logs"


class Config(BaseModel):
    """Main configuration model"""
    opencode: OpenCodeConfig = Field(default_factory=OpenCodeConfig)
    opencode_launcher: OpenCodeLauncherConfig = Field(default_factory=OpenCodeLauncherConfig)
    server: ServerConfig = Field(default_factory=ServerConfig)
    cors: CORSConfig = Field(default_factory=CORSConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    session: SessionConfig = Field(default_factory=SessionConfig)
    request: RequestConfig = Field(default_factory=RequestConfig)
    sse: SSEConfig = Field(default_factory=SSEConfig)


def load_yaml_config(config_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Load configuration from YAML file.

    Also loads .env file from the project root for local development.
    """
    # Load .env file first (if it exists)
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        load_dotenv(str(env_path))

    if config_path is None:
        # Look for config.yaml in the same directory as this file
        config_path = Path(__file__).parent.parent / "config.yaml"

    if not config_path.exists():
        return {}

    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def get_env_override(key: str, default: Any = None) -> Any:
    """Get value from environment variable, with prefix"""
    # Try with WRAPPER_ prefix first
    env_key = f"WRAPPER_{key.upper()}"
    value = os.environ.get(env_key)
    if value is not None:
        return value

    # Try without prefix
    env_key = key.upper()
    value = os.environ.get(env_key)
    if value is not None:
        return value

    return default


def apply_env_overrides(config_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Apply environment variable overrides to configuration"""
    # OpenCode overrides
    if "OPENCODE_HOST" in os.environ:
        config_dict.setdefault("opencode", {})["host"] = os.environ["OPENCODE_HOST"]
    if "OPENCODE_PORT" in os.environ:
        config_dict.setdefault("opencode", {})["port"] = int(os.environ["OPENCODE_PORT"])
    if "OPENCODE_USERNAME" in os.environ:
        config_dict.setdefault("opencode", {})["username"] = os.environ["OPENCODE_USERNAME"]
    if "OPENCODE_PASSWORD" in os.environ:
        config_dict.setdefault("opencode", {})["password"] = os.environ["OPENCODE_PASSWORD"]

    # OpenCode Launcher overrides
    if "OPENCODE_LAUNCHER_ENABLED" in os.environ:
        config_dict.setdefault("opencode_launcher", {})["enabled"] = os.environ["OPENCODE_LAUNCHER_ENABLED"].lower() == "true"
    if "OPENCODE_LAUNCHER_STRICT" in os.environ:
        config_dict.setdefault("opencode_launcher", {})["strict"] = os.environ["OPENCODE_LAUNCHER_STRICT"].lower() == "true"
    if "OPENCODE_PATH" in os.environ:
        config_dict.setdefault("opencode_launcher", {})["opencode_path"] = os.environ["OPENCODE_PATH"]
    if "OPENCODE_LAUNCHER_HOST" in os.environ:
        config_dict.setdefault("opencode_launcher", {})["host"] = os.environ["OPENCODE_LAUNCHER_HOST"]
    if "OPENCODE_LAUNCHER_PORT" in os.environ:
        config_dict.setdefault("opencode_launcher", {})["port"] = int(os.environ["OPENCODE_LAUNCHER_PORT"])
    if "OPENCODE_LAUNCHER_PASSWORD" in os.environ:
        config_dict.setdefault("opencode_launcher", {})["password"] = os.environ["OPENCODE_LAUNCHER_PASSWORD"]

    # Server overrides
    if "WRAPPER_HOST" in os.environ:
        config_dict.setdefault("server", {})["host"] = os.environ["WRAPPER_HOST"]
    if "WRAPPER_PORT" in os.environ:
        config_dict.setdefault("server", {})["port"] = int(os.environ["WRAPPER_PORT"])

    # CORS overrides
    if "CORS_ORIGINS" in os.environ:
        config_dict.setdefault("cors", {})["origins"] = os.environ["CORS_ORIGINS"].split(",")

    # Logging overrides
    if "LOG_LEVEL" in os.environ:
        config_dict.setdefault("logging", {})["level"] = os.environ["LOG_LEVEL"]

    # SSE overrides
    if "SSE_ENABLED" in os.environ:
        config_dict.setdefault("sse", {})["enabled"] = os.environ["SSE_ENABLED"].lower() == "true"

    return config_dict


def load_config(config_path: Optional[Path] = None) -> Config:
    """Load complete configuration with environment overrides"""
    # Load from YAML
    config_dict = load_yaml_config(config_path)

    # Apply environment overrides
    config_dict = apply_env_overrides(config_dict)

    # Create config object
    return Config(**config_dict)


# Global config instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get global configuration instance"""
    global _config
    if _config is None:
        _config = load_config()
    return _config


def reset_config() -> None:
    """Reset configuration (useful for testing)"""
    global _config
    _config = None
