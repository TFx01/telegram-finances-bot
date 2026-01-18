"""
Telegram Bot Configuration Module

Loads configuration from:
1. .env file (for local development)
2. config.yaml (for project settings)
3. Environment variables (highest priority)

Supports both direct values and environment variable references.

Usage in config.yaml:
  bot_token: "${TELEGRAM_BOT_TOKEN}"          # Required env var
  chat_id: "${TELEGRAM_CHAT_ID:-12345}"       # Env var with default
  debug: "${DEBUG_MODE:-false}"               # Env var with default value

Environment variables take precedence over config file values.
"""

import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field


def parse_env_var(value: Any) -> Any:
    """
    Parse a value that might contain environment variable references.
    
    Supports formats:
      "${VAR}"           - Required env var (error if not set)
      "${VAR:-default}"  - Optional with default value
      "${VAR:-}"         - Optional with empty default
    
    Examples:
      "${TELEGRAM_TOKEN}"           -> returns env var or error
      "${TELEGRAM_ID:-12345}"       -> returns env var or "12345"
      "${OPTIONAL:-}"               -> returns env var or ""
      "direct_value"                -> returns "direct_value"
      12345                         -> returns 12345
    """
    if not isinstance(value, str):
        return value
    
    # Match ${VAR_NAME} or ${VAR_NAME:-default}
    pattern = r'\$\{([^:-]+)(?::-([^\}]*))?\}'
    match = re.search(pattern, value)
    
    if not match:
        return value
    
    env_var = match.group(1)
    default_value = match.group(2) or ""
    
    env_value = os.environ.get(env_var)
    
    if env_value is None:
        if default_value == "" and match.group(0) == match.group():
            # Full match with no default - this is required
            raise ValueError(
                f"Environment variable '{env_var}' is required but not set. "
                f"Either set it or use '${{{env_var}:-default}}' for optional values."
            )
        return default_value
    
    return env_value


def recursively_parse_env_vars(config: Any) -> Any:
    """Recursively parse environment variables in config dict/list"""
    if isinstance(config, dict):
        return {k: recursively_parse_env_vars(v) for k, v in config.items()}
    elif isinstance(config, list):
        return [recursively_parse_env_vars(item) for item in config]
    else:
        return parse_env_var(config)


class TelegramConfig(BaseModel):
    """Telegram bot configuration"""
    bot_token: str = ""
    chat_id: int = 0


class WebhookConfig(BaseModel):
    """Webhook configuration"""
    enabled: bool = False
    host: str = "0.0.0.0"
    port: int = 8080
    path: str = "/webhook"


class WrapperConfig(BaseModel):
    """Wrapper server configuration"""
    url: str = "http://localhost:5147"
    timeout: int = 300


class TailscaleConfig(BaseModel):
    """Tailscale SSH tunnel configuration"""
    enabled: bool = False
    opencode_ip: str = "100.x.x.x"
    ssh_port: int = 22
    ssh_user: str = "username"
    ssh_key: str = "~/.ssh/id_ed25519"


class SupabaseConfig(BaseModel):
    """Supabase database configuration"""
    enabled: bool = False
    url: str = ""
    key: str = ""


class LoggingConfig(BaseModel):
    """Logging configuration"""
    level: str = "INFO"
    format: str = "[{time}] {level}: {message}"
    dir: str = "logs"


class SessionConfig(BaseModel):
    """Session configuration"""
    timeout: int = 3600
    storage: str = "memory"


class FeaturesConfig(BaseModel):
    """Feature flags"""
    voice_enabled: bool = True
    image_enabled: bool = True
    document_enabled: bool = True


class SecurityConfig(BaseModel):
    """Security and access control configuration"""
    allowed_chat_ids: List[int] = Field(default_factory=list)
    mode: str = "both"  # "group", "private", or "both"
    block_unknown: bool = False
    
    def model_dump(self, **kwargs):
        """Custom dump to filter out empty/invalid chat IDs"""
        data = super().model_dump(**kwargs)
        # Filter out invalid chat IDs (0 or empty strings that got converted)
        data["allowed_chat_ids"] = [cid for cid in data.get("allowed_chat_ids", []) if cid and cid != 0]
        return data


class Config(BaseModel):
    """Main configuration model"""
    telegram: TelegramConfig = Field(default_factory=TelegramConfig)
    webhook: WebhookConfig = Field(default_factory=WebhookConfig)
    wrapper: WrapperConfig = Field(default_factory=WrapperConfig)
    tailscale: TailscaleConfig = Field(default_factory=TailscaleConfig)
    supabase: SupabaseConfig = Field(default_factory=SupabaseConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    session: SessionConfig = Field(default_factory=SessionConfig)
    features: FeaturesConfig = Field(default_factory=FeaturesConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)


def load_yaml_config(config_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Load configuration from YAML file and parse environment variables.
    
    Also loads .env file from the project root for local development.
    """
    # Load .env file first (if it exists) - these will be overridden by config.yaml
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        load_dotenv(str(env_path))
    
    if config_path is None:
        config_path = Path(__file__).parent.parent / "config.yaml"
    
    if not config_path.exists():
        return {}
    
    with open(config_path, "r", encoding="utf-8") as f:
        raw_config = yaml.safe_load(f) or {}
    
    # Parse environment variable references
    return recursively_parse_env_vars(raw_config)


def apply_env_overrides(config_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Apply environment variable overrides to configuration"""
    # Telegram overrides
    if "TELEGRAM_BOT_TOKEN" in os.environ:
        config_dict.setdefault("telegram", {})["bot_token"] = os.environ["TELEGRAM_BOT_TOKEN"]
    if "TELEGRAM_CHAT_ID" in os.environ:
        config_dict.setdefault("telegram", {})["chat_id"] = int(os.environ["TELEGRAM_CHAT_ID"])
    
    # Webhook overrides
    if "WEBHOOK_ENABLED" in os.environ:
        config_dict.setdefault("webhook", {})["enabled"] = os.environ["WEBHOOK_ENABLED"].lower() == "true"
    if "WEBHOOK_HOST" in os.environ:
        config_dict.setdefault("webhook", {})["host"] = os.environ["WEBHOOK_HOST"]
    if "WEBHOOK_PORT" in os.environ:
        config_dict.setdefault("webhook", {})["port"] = int(os.environ["WEBHOOK_PORT"])
    
    # Wrapper overrides
    if "WRAPPER_URL" in os.environ:
        config_dict.setdefault("wrapper", {})["url"] = os.environ["WRAPPER_URL"]
    if "WRAPPER_TIMEOUT" in os.environ:
        config_dict.setdefault("wrapper", {})["timeout"] = int(os.environ["WRAPPER_TIMEOUT"])
    
    # Logging overrides
    if "LOG_LEVEL" in os.environ:
        config_dict.setdefault("logging", {})["level"] = os.environ["LOG_LEVEL"]
    
    return config_dict


def load_config(config_path: Optional[Path] = None) -> Config:
    """Load complete configuration with environment overrides"""
    config_dict = load_yaml_config(config_path)
    config_dict = apply_env_overrides(config_dict)
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
