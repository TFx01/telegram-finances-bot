# Telegram Bot Setup Tutorial

Complete guide to configuring your Telegram bot for the telegram-communication project.

---

## Table of Contents

1. [Creating Your Telegram Bot](#1-creating-your-telegram-bot)
2. [Getting Your Chat ID](#2-getting-your-chat-id)
3. [Configuring the Bot](#3-configuring-the-bot)
   - [Option A: Using .env file](#option-a-using-env-file-recommended)
   - [Option B: Using config.yaml](#option-b-using-configyaml)
   - [Option C: Environment variables](#option-c-environment-variables)
4. [Running in Polling Mode (Development)](#4-running-in-polling-mode-development)
5. [Running in Webhook Mode (Production)](#5-running-in-webhook-mode-production)
6. [Testing Your Bot](#6-testing-your-bot)
7. [Troubleshooting](#7-troubleshooting)

---

## 1. Creating Your Telegram Bot

### Step 1.1: Talk to BotFather

1. Open Telegram
2. Search for **@BotFather** (official Telegram bot creator)
3. Click **Start** to begin

### Step 1.2: Create a New Bot

Send the following command to BotFather:

```
/newbot
```

BotFather will ask you for:
1. **Bot name** - A friendly name (e.g., "My Finance Assistant")
2. **Bot username** - Must end with "bot" (e.g., "my_finance_bot")

### Step 1.3: Get Your Bot Token

After creating the bot, BotFather will show you:

```
Done! Congratulations on your new bot. You will find it at...
https://t.me/your_bot_name

Use this token to access the HTTP API:
123456789:ABCdefGHIjklMNOpqrsTUVwxyz

Keep your token secure and store it safely!
```

**⚠️ IMPORTANT:** Copy this token! You'll need it later.

Example token format:
```
5501234567:AAE7Xy8BeT9Cf0DhEF1GhIjKLmnOpqrST
```

### Step 1.4: Configure Bot Settings (Optional but Recommended)

Set a bot description:
```
/setdescription
```
Then select your bot and enter:
```
I am your AI assistant. Send me a message and I'll help you with analysis, research, and more!
```

Set commands menu:
```
/setcommands
```
Then select your bot and enter:
```
start - Start a conversation
help - Show help message
new - Start a new session
status - Check session status
end - End current session
```

---

## 2. Getting Your Chat ID

Your Chat ID is a unique number that identifies your Telegram account.

### Method 1: Using @userinfobot (Easiest)

1. Open Telegram
2. Search for **@userinfobot**
3. Click **Start**
4. The bot will immediately show your information:

```
ID: 123456789
First Name: Your Name
Username: your_username
```

**Your Chat ID is the number after "ID:"** (e.g., `123456789`)

### Method 2: Using Telegram API (Advanced)

If you prefer using the command line:

```bash
# Get your user info via Telegram API
curl -s https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getMe
```

Replace `<YOUR_BOT_TOKEN>` with your actual bot token.

---

## 3. Configuring the Bot

### Step 3.1: Set Environment Variables (Recommended)

Add these to your shell profile (`.zshrc` or `.bashrc`):

```bash
# For Zsh
echo 'export TELEGRAM_BOT_TOKEN="your-bot-token-here"' >> ~/.zshrc
echo 'export TELEGRAM_CHAT_ID="your-chat-id-here"' >> ~/.zshrc
echo 'export WRAPPER_URL="http://localhost:5147"' >> ~/.zshrc

# Reload your profile
source ~/.zshrc
```

Or set them temporarily in your current terminal:

```bash
export TELEGRAM_BOT_TOKEN="5501234567:AAE7Xy8BeT9Cf0DhEF1GhIjKLmnOpqrST"
export TELEGRAM_CHAT_ID="123456789"
export WRAPPER_URL="http://localhost:5147"
```

---

## 3. Configuring the Bot

You have **3 options** to configure the bot. Choose the one you prefer!

### Option A: Using .env file (Recommended)

This is the easiest way for local development.

**Step 3.1: Create the .env file**

```bash
cd telegram_bot

# Copy the example file
cp .env.example .env

# Edit it with your values
nano .env
```

**Step 3.2: Fill in your .env file**

```bash
# Required
TELEGRAM_BOT_TOKEN=your-bot-token-here

# Optional (for group mode)
GROUP_CHAT_ID=-1001234567890

# Optional (defaults provided)
WRAPPER_URL=http://localhost:5147
LOG_LEVEL=INFO
```

**Step 3.3: Verify Configuration**

```bash
cd telegram_bot
make check-config
```

---

### Option B: Using config.yaml

Edit `telegram_bot/config.yaml`:

```yaml
telegram:
  bot_token: "${TELEGRAM_BOT_TOKEN}"  # Reads from env var
  chat_id: "${TELEGRAM_CHAT_ID:-0}"

security:
  allowed_chat_ids:
    - "${GROUP_CHAT_ID}"  # Set GROUP_CHAT_ID in .env
  mode: "group"
  block_unknown: true

wrapper:
  url: "http://localhost:5147"
  timeout: 300

logging:
  level: "${LOG_LEVEL:-INFO}"
  dir: "logs"

session:
  timeout: 3600
  storage: "memory"
```

The `${VAR:-default}` syntax means:
- `${TELEGRAM_BOT_TOKEN}` - Required (error if not set)
- `${TELEGRAM_CHAT_ID:-0}` - Optional, defaults to 0
- `${LOG_LEVEL:-INFO}` - Optional, defaults to INFO

---

### Option C: Environment variables (Terminal)

Set them in your current terminal:

```bash
export TELEGRAM_BOT_TOKEN="5501234567:AAE7Xy8BeT9Cf0DhEF1GhIjKLmnOpqrST"
export TELEGRAM_CHAT_ID="123456789"
export WRAPPER_URL="http://localhost:5147"
```

Or add to your shell profile (`.zshrc` or `.bashrc`):

```bash
echo 'export TELEGRAM_BOT_TOKEN="your-token"' >> ~/.zshrc
echo 'export GROUP_CHAT_ID="-1001234567890"' >> ~/.zshrc
source ~/.zshrc
```

---

### Configuration Priority

The bot loads configuration in this order (later = higher priority):

1. **.env file** (for local development)
2. **config.yaml** (project settings)
3. **Environment variables** (highest priority)

This means you can use a mix:
- Sensitive values in `.env` (not committed to git)
- Project settings in `config.yaml`
- Override anything with environment variables

---

## 4. Running in Polling Mode (Development)

Polling mode is perfect for development because:
- Easy to debug
- No external server needed
- See logs in real-time

### Step 4.1: Install Dependencies

```bash
cd telegram_bot
make setup
```

### Step 4.2: Start the Wrapper Server (Required First!)

Open a **new terminal** and run:

```bash
cd wrapper_server
make run
```

You should see:
```
╔════════════════════════════════════════════════════════════════════╗
║                     Wrapper Server Started                         ║
╠════════════════════════════════════════════════════════════════════╣
║  URL:        http://0.0.0.0:5147                        ║
║  OpenCode:   http://127.0.0.1:4096                       ║
```

### Step 4.3: Start the Telegram Bot

In your **first terminal**, run:

```bash
cd telegram_bot
make run
```

You should see:
```
🤖 Telegram bot started in polling mode...
```

### Step 4.4: Test Your Bot

1. Open Telegram
2. Find your bot (the username you created)
3. Send `/start`
4. You should receive a welcome message!

---

## 5. Running in Webhook Mode (Production)

Webhook mode is better for production because:
- More efficient (no constant polling)
- Faster response times
- Uses less resources

### Prerequisites for Webhook Mode

1. **Public IP or Domain** - Your server must be accessible from the internet
2. **SSL Certificate** - Telegram requires HTTPS for webhooks
3. **Domain Name** - Recommended (can use DuckDNS for free dynamic DNS)

### Option 5.1: Using ngrok (Quick Testing)

Perfect for testing webhooks without a real domain:

```bash
# Install ngrok (macOS)
brew install ngrok

# Start ngrok tunnel to your webhook port
ngrok http 8080
```

Note the HTTPS URL ngrok provides (e.g., `https://abc123.ngrok.io`).

### Option 5.2: Using Cloudflare Tunnel (Free & Production-Ready)

Best free option for persistent webhooks:

```bash
# Install cloudflared
brew install cloudflare/cloudflare/cloudflared

# Create a tunnel (get your tunnel URL from Cloudflare dashboard)
cloudflared tunnel --url http://localhost:8080
```

### Step 5.1: Configure Webhook Settings

Edit `telegram_bot/config.yaml`:

```yaml
webhook:
  enabled: true
  host: "0.0.0.0"
  port: 8080
  path: "/webhook"
```

### Step 5.2: Set Webhook URL with Telegram

```bash
# Replace YOUR_DOMAIN with your actual domain
curl -F "url=https://your-domain.com/webhook" \
     https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook
```

Example:
```bash
curl -F "url=https://mybot.example.com/webhook" \
     https://api.telegram.org/bot5501234567:AAE7Xy8BeT9Cf0DhEF1GhIjKLmnOpqrST/setWebhook
```

### Step 5.3: Start the Bot

```bash
cd telegram_bot
make run-webhook PORT=8080
```

### Step 5.4: Verify Webhook is Active

```bash
# Check webhook status
curl https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getWebhookInfo
```

---

## 6. Testing Your Bot

### Quick Test Commands

| Command | Expected Response |
|---------|-------------------|
| `/start` | Welcome message with instructions |
| `/help` | Help text with available commands |
| `/status` | Session status information |
| `/new` | Confirmation of new session |
| `/end` | Session ended message |

### Manual Testing Checklist

- [ ] Bot responds to `/start`
- [ ] Bot responds to `/help`
- [ ] Bot responds to text messages
- [ ] Bot creates new sessions with `/new`
- [ ] Session persists across messages
- [ ] `/status` shows correct session info
- [ ] `/end` properly closes session

### Debug Mode

For verbose logging:

```bash
export LOG_LEVEL=DEBUG
cd telegram_bot
make run
```

---

## 7. Troubleshooting

### Problem: "Bad Request: Chat not found"

**Cause:** Chat ID is incorrect or bot can't see the user

**Solution:**
1. Make sure you've started a conversation with your bot
2. Verify your Chat ID with @userinfobot
3. Check that the bot token is correct

### Problem: "Unauthorized: Bot token invalid"

**Cause:** Incorrect or expired bot token

**Solution:**
1. Open Telegram and search for @BotFather
2. Send `/token` to see your current tokens
3. Create a new token if needed
4. Update your environment variable

### Problem: Bot not responding to messages

**Cause:** Multiple possible issues

**Solution:**
1. Check bot is running: `make check-config`
2. Check Wrapper Server is running
3. Check logs in `telegram_bot/logs/`
4. Restart both servers

### Problem: Webhook returning 404

**Cause:** Webhook URL not set correctly

**Solution:**
1. Verify webhook URL is HTTPS
2. Check firewall rules allow traffic on port 8080
3. Verify Telegram can reach your server
4. Test with: `curl -v https://your-domain.com/webhook`

### Problem: "Connection refused" to Wrapper Server

**Cause:** Wrapper Server not running

**Solution:**
1. Start Wrapper Server first: `cd wrapper_server && make run`
2. Verify it's running on correct port (5147)
3. Check for errors in wrapper_server logs

### Problem: "Module not found" errors

**Cause:** Python path not set correctly

**Solution:**
1. Run from project directory: `cd telegram_bot`
2. Use the Makefile: `make run` (not `python src/bot.py`)
3. Ensure virtual environment is activated

### Getting Help

If you're still having issues:

1. Check logs: `tail -f telegram_bot/logs/bot_$(date +%Y-%m-%d).log`
2. Run with debug mode: `LOG_LEVEL=DEBUG make run`
3. Search existing issues in the project

---

## Quick Reference: All Commands

```bash
# Setup
cd telegram_bot
make setup

# Run in polling mode (development)
make run

# Run in webhook mode (production)
make run-webhook PORT=8080

# Check configuration
make check-config

# View logs
make logs

# Clean up
make clean
```

---

## Environment Variables Quick Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `TELEGRAM_BOT_TOKEN` | Yes | - | Bot token from @BotFather |
| `TELEGRAM_CHAT_ID` | Yes | - | Your Chat ID from @userinfobot |
| `WRAPPER_URL` | No | http://localhost:5147 | Wrapper Server URL |
| `WRAPPER_TIMEOUT` | No | 300 | Request timeout in seconds |
| `LOG_LEVEL` | No | INFO | DEBUG, INFO, WARNING, ERROR |

---

**🎉 You're all set! Your Telegram bot is ready to use!**
