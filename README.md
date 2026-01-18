# Telegram Communication System

Complete implementation of a Telegram bot that interfaces with OpenCode AI assistant.

## Architecture

```
┌─────────────┐                    ┌─────────────────┐                    ┌─────────────┐
│   Telegram  │                    │   Telegram Bot  │                    │   Wrapper   │
│   User      │ ◄───────────────► │   (Python)      │ ◄───────────────► │   Server    │
└─────────────┘                    └─────────────────┘                    └─────────────┘
                                                                      │
                                                                      ▼
                                                                    ┌─────────────┐
                                                                    │   OpenCode  │
                                                                    │   (:4096)   │
                                                                    └─────────────┘
```

## Projects

### 1. telegram_bot

A Telegram bot that provides a conversational interface to OpenCode.

**Features:**
- Text message handling
- Voice note transcription
- Image analysis support
- Session management
- Interactive keyboards
- Webhook support

**Quick Start:**
```bash
cd telegram_bot
make setup
make run
```

### 2. wrapper_server

A FastAPI-based REST API bridge between the Telegram bot and OpenCode.

**Features:**
- REST API for session management
- Automatic authentication with OpenCode
- CORS support
- Health check endpoints

**Quick Start:**
```bash
cd wrapper_server
make setup
make run
```

## Prerequisites

- Python 3.11+
- Telegram Bot Token (get from @BotFather)
- OpenCode running on localhost:4096
- Tailscale (optional, for remote access)

## Installation

1. **Start OpenCode:**
   ```bash
   opencode --port 4096
   ```

2. **Start Wrapper Server:**
   ```bash
   cd wrapper_server
   make run
   ```

3. **Start Telegram Bot:**
   ```bash
   cd telegram_bot
   make run
   ```

## Environment Variables

### Telegram Bot

| Variable | Description |
|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | Telegram bot token |
| `TELEGRAM_CHAT_ID` | Your Telegram chat ID |
| `WRAPPER_URL` | Wrapper Server URL (default: http://localhost:5147) |

### Wrapper Server

| Variable | Description |
|----------|-------------|
| `OPENCODE_HOST` | OpenCode host (default: 127.0.0.1) |
| `OPENCODE_PORT` | OpenCode port (default: 4096) |
| `OPENCODE_PASSWORD` | OpenCode server password |
| `WRAPPER_PORT` | Wrapper Server port (default: 5147) |

## Documentation

- [Telegram Bot README](./telegram_bot/README.md)
- [Wrapper Server README](./wrapper_server/README.md)
- [Setup Guide](./docs/TELEGRAM_REPO_SETUP.md)

## License

MIT
