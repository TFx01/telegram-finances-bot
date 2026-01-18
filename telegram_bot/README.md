# Telegram Bot

A Telegram bot that interfaces with OpenCode AI assistant through the Wrapper Server.

## Overview

This bot provides a conversational interface to OpenCode, allowing you to:
- Send text messages for analysis
- Send voice notes for transcription
- Send images for analysis
- Manage conversation sessions

```
┌─────────────┐      HTTP       ┌─────────────────┐      HTTP       ┌─────────────┐
│   Telegram  │                 │   Telegram Bot  │                 │   Wrapper   │
│   User      │ ◄─────────────► │   (Python)      │ ─────────────► │   Server    │
└─────────────┘                 └─────────────────┘                └─────────────┘
```

## Features

- Text message handling
- Voice note transcription
- Image analysis support
- Document handling
- Session management
- Interactive keyboards
- Webhook support for production

## Installation

```bash
# Clone the repository
cd telegram_bot

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Configuration

Copy `config.yaml.example` to `config.yaml` and modify:

```yaml
telegram:
  bot_token: ""  # Get from @BotFather
  chat_id: 0     # Your chat ID

wrapper:
  url: "http://localhost:5147"
  timeout: 300

webhook:
  enabled: false
  host: "0.0.0.0"
  port: 8080
  path: "/webhook"
```

Or set environment variables:

```bash
export TELEGRAM_BOT_TOKEN=your-bot-token
export TELEGRAM_CHAT_ID=your-chat-id
export WRAPPER_URL=http://localhost:5147
```

## Usage

### Start the Bot

```bash
# Polling mode (development)
make run

# Webhook mode (production)
make run-webhook PORT=8080

# Development with auto-reload
make run-dev
```

### Available Commands

| Command | Description |
|---------|-------------|
| `/start` | Start a new conversation |
| `/help` | Show help message |
| `/new` | Create a new session (ends current one) |
| `/status` | Check current session status |
| `/end` | End the current session |
| `/cancel` | Cancel current operation |

## Development

```bash
# Install dependencies and run tests
make setup
make test

# Run linter
make lint

# Fix linter issues
make lint-fix
```

## Architecture

```
src/
├── __init__.py          # Package exports
├── bot.py               # Main bot application
├── config.py            # Configuration loader
├── logger.py            # Logging setup
├── session_manager.py   # Session persistence
├── webhook_handler.py   # FastAPI webhook server
├── wrapper_client.py    # Wrapper Server client
└── keyboards/
    ├── __init__.py
    └── main_menu.py     # Telegram keyboards
```

## Integration with Wrapper Server

The bot expects the Wrapper Server to be running on `http://localhost:5147`:

```
Telegram User → Telegram Bot → Wrapper Server → OpenCode (:4096)
```

Make sure to start the Wrapper Server first:

```bash
# In wrapper_server directory
cd wrapper_server
make run
```

## License

MIT
