.PHONY: run install test lint clean setup run-webhook run-dev

# Colors
GREEN = \033[0;32m
YELLOW = \033[0;33m
NC = \033[0m # No Color

# Default port
TELEGRAM_PORT ?= 8080
WEBHOOK_PORT ?= 8080

setup:
	@echo "$(GREEN)Creating virtual environment...$(NC)"
	python3 -m venv venv
	@echo "$(GREEN)Installing dependencies...$(NC)"
	. venv/bin/activate && pip install -r requirements.txt
	@echo "$(GREEN)Setup complete!$(NC)"

install: setup

run: setup
	@echo "$(GREEN)Starting Telegram Bot in polling mode...$(NC)"
	. venv/bin/activate && python -m src.bot

run-webhook: setup
	@echo "$(GREEN)Starting Telegram Bot in webhook mode on port $(WEBHOOK_PORT)...$(NC)"
	. venv/bin/activate && python -m src.bot --webhook --port $(WEBHOOK_PORT)

run-dev: setup
	@echo "$(GREEN)Starting Telegram Bot in development mode...$(NC)"
	. venv/bin/activate && python -m src.bot --debug

test:
	@echo "$(GREEN)Running tests...$(NC)"
	. venv/bin/activate && pytest tests/ -v --tb=short

test-coverage:
	@echo "$(GREEN)Running tests with coverage...$(NC)"
	. venv/bin/activate && pytest tests/ -v --tb=short --cov=src --cov-report=term-missing

lint:
	@echo "$(GREEN)Running linter...$(NC)"
	. venv/bin/activate && ruff check src/
	. venv/bin/activate && ruff format --check src/

lint-fix:
	@echo "$(GREEN)Fixing linter issues...$(NC)"
	. venv/bin/activate && ruff check src/ --fix
	. venv/bin/activate && ruff format src/

clean:
	@echo "$(GREEN)Cleaning up...$(NC)"
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name ".pytest_cache" -delete 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .coverage htmlcov 2>/dev/null || true
	rm -rf venv/ 2>/dev/null || true
	rm -rf sessions.json logs/ 2>/dev/null || true
	@echo "$(GREEN)Clean complete!$(NC)"

logs:
	@echo "$(GREEN)Showing recent logs...$(NC)"
	tail -f logs/bot_$$(date +%Y-%m-%d).log 2>/dev/null || echo "No logs yet. Run the bot first."

check-config:
	@echo "$(GREEN)Checking configuration...$(NC)"
	. venv/bin/activate && python -c "from src.config import get_config; c = get_config(); print(f'Telegram: configured={bool(c.telegram.bot_token)}'); print(f'Wrapper: {c.wrapper.url}'); print(f'Webhook: {c.webhook.enabled}')"

help:
	@echo "Telegram Bot Makefile"
	@echo ""
	@echo "Commands:"
	@echo "  setup        - Create virtual environment and install dependencies"
	@echo "  install      - Alias for setup"
	@echo "  run          - Start bot in polling mode"
	@echo "  run-webhook  - Start bot in webhook mode"
	@echo "  run-dev      - Start in development mode"
	@echo "  test         - Run tests"
	@echo "  test-coverage- Run tests with coverage report"
	@echo "  lint         - Check code style"
	@echo "  lint-fix     - Fix code style issues"
	@echo "  clean        - Remove generated files and cache"
	@echo "  logs         - Show logs"
	@echo "  check-config - Verify configuration"
	@echo "  help         - Show this help message"
