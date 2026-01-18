# Wrapper Server

A FastAPI-based REST API bridge between Telegram bot and OpenCode AI assistant.

## Overview

This server exposes REST endpoints that the Telegram bot uses to communicate with OpenCode's native REST API.

```
┌─────────────────┐      HTTP       ┌─────────────────┐      HTTP       ┌─────────────┐
│  Telegram Bot   │ ─────────────► │ Wrapper Server  │ ─────────────► │  OpenCode   │
│  (Python)       │                │  (FastAPI)      │                │  (:4096)    │
└─────────────────┘                └─────────────────┘                └─────────────┘
```

## Features

- REST API for session management
- Automatic authentication with OpenCode
- CORS support for browser clients
- Health check endpoints
- Session creation and messaging
- Agent listing

## Installation

```bash
# Clone the repository
cd wrapper_server

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Configuration

Copy `config.yaml.example` to `config.yaml` and modify:

```yaml
opencode:
  host: "127.0.0.1"
  port: 4096
  username: "opencode"
  password: ""  # Set via OPENCODE_SERVER_PASSWORD env var

server:
  host: "0.0.0.0"
  port: 5147

logging:
  level: "INFO"
```

Or set environment variables:

```bash
export OPENCODE_HOST=127.0.0.1
export OPENCODE_PORT=4096
export OPENCODE_PASSWORD=your-password
export WRAPPER_PORT=5147
```

## Usage

### Start the Server

```bash
# Development mode with auto-reload
make run-dev

# Production mode
make run
```

### Available Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/agents` | List available agents |
| POST | `/session/start` | Create new session |
| POST | `/session/{id}/message` | Send message |
| GET | `/session/{id}/status` | Get session status |
| DELETE | `/session/{id}` | Delete session |
| POST | `/session/{id}/abort` | Abort running session |

### API Examples

```bash
# Start a new session
curl -X POST http://localhost:5147/session/start \
  -H "Content-Type: application/json" \
  -d '{"chat_id": 12345, "title": "Test Session"}'

# Send a message
curl -X POST http://localhost:5147/session/{session_id}/message \
  -H "Content-Type: application/json" \
  -d '{"chat_id": 12345, "message": "Hello, analyze my finances"}'
```

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
├── __init__.py       # Package exports
├── config.py         # Configuration loader
├── opencode_client.py # OpenCode REST API client
└── wrapper_server.py  # FastAPI application
```

## License

MIT
