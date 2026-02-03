.PHONY: help install setup venv venv-activate run docker-build docker-up docker-down docker-logs clean clean-venv test lint format

# Default target
.DEFAULT_GOAL := help

# Variables
PYTHON := python
PIP := pip
STREAMLIT := streamlit
DOCKER_COMPOSE := docker-compose
APP_FILE := app.py
VENV := venv
VENV_BIN := $(VENV)/bin
VENV_PYTHON := $(VENV_BIN)/python
VENV_PIP := $(VENV_BIN)/pip
VENV_STREAMLIT := $(VENV_BIN)/streamlit

# Detect OS for path handling
ifeq ($(OS),Windows_NT)
	VENV_BIN := $(VENV)/Scripts
	VENV_PYTHON := $(VENV_BIN)/python.exe
	VENV_PIP := $(VENV_BIN)/pip.exe
	VENV_STREAMLIT := $(VENV_BIN)/streamlit.exe
endif

# Colors for output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
NC := \033[0m # No Color

help: ## Show this help message
	@echo "$(BLUE)Blog Writing Agent - Available Commands$(NC)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "$(GREEN)%-20s$(NC) %s\n", $$1, $$2}'

# ==================== Setup ====================

venv: ## Create virtual environment
	@echo "$(BLUE)Creating virtual environment...$(NC)"
	@if [ -d "$(VENV)" ]; then \
		echo "$(YELLOW)⚠ Virtual environment already exists$(NC)"; \
	else \
		$(PYTHON) -m venv $(VENV); \
		echo "$(GREEN)✓ Virtual environment created$(NC)"; \
	fi
	@echo "$(YELLOW)To activate: source $(VENV_BIN)/activate (Linux/Mac) or $(VENV)\Scripts\activate (Windows)$(NC)"

venv-install: venv ## Create venv and install dependencies
	@echo "$(BLUE)Installing dependencies in virtual environment...$(NC)"
	$(VENV_PIP) install --upgrade pip
	$(VENV_PIP) install -r requirements.txt
	@echo "$(GREEN)✓ Dependencies installed in venv$(NC)"

install: ## Install Python dependencies (current environment)
	@echo "$(BLUE)Installing dependencies...$(NC)"
	$(PIP) install -r requirements.txt
	@echo "$(GREEN)✓ Dependencies installed$(NC)"

setup: ## Initial setup (create venv + install + create .env)
	@echo "$(BLUE)Setting up project...$(NC)"
	$(MAKE) venv-install
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "$(YELLOW)⚠ Created .env file. Please edit it with your API keys.$(NC)"; \
	else \
		echo "$(GREEN)✓ .env file already exists$(NC)"; \
	fi
	@mkdir -p images outputs
	@echo "$(GREEN)✓ Setup complete$(NC)"
	@echo "$(YELLOW)Next: Edit .env with your API keys, then run 'make venv-run'$(NC)"

setup-no-venv: ## Initial setup without virtual environment
	@echo "$(BLUE)Setting up project (no venv)...$(NC)"
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "$(YELLOW)⚠ Created .env file. Please edit it with your API keys.$(NC)"; \
	else \
		echo "$(GREEN)✓ .env file already exists$(NC)"; \
	fi
	$(MAKE) install
	@mkdir -p images outputs
	@echo "$(GREEN)✓ Setup complete$(NC)"

# ==================== Development ====================

venv-run: ## Run the Streamlit app using virtual environment
	@echo "$(BLUE)Starting Streamlit app (venv)...$(NC)"
	@if [ ! -d "$(VENV)" ]; then \
		echo "$(YELLOW)⚠ Virtual environment not found. Run 'make setup' first.$(NC)"; \
		exit 1; \
	fi
	@echo "$(YELLOW)Open http://localhost:8501 in your browser$(NC)"
	$(VENV_STREAMLIT) run $(APP_FILE) --server.port=8501

run: ## Run the Streamlit application (current environment)
	@echo "$(BLUE)Starting Streamlit app...$(NC)"
	@echo "$(YELLOW)Open http://localhost:8501 in your browser$(NC)"
	$(STREAMLIT) run $(APP_FILE) --server.port=8501

run-debug: ## Run with debug logging
	@echo "$(BLUE)Starting Streamlit app in debug mode...$(NC)"
	$(STREAMLIT) run $(APP_FILE) --server.port=8501 --logger.level=debug

venv-shell: ## Activate virtual environment shell
	@echo "$(BLUE)Activating virtual environment...$(NC)"
	@echo "Run: source $(VENV_BIN)/activate (Linux/Mac) or $(VENV)\Scripts\activate (Windows)"

# ==================== Docker ====================

docker-build: ## Build Docker image
	@echo "$(BLUE)Building Docker image...$(NC)"
	$(DOCKER_COMPOSE) build
	@echo "$(GREEN)✓ Docker image built$(NC)"

docker-up: ## Start Docker containers
	@echo "$(BLUE)Starting Docker containers...$(NC)"
	@if [ ! -f .env ]; then \
		echo "$(YELLOW)⚠ No .env file found. Creating from .env.example...$(NC)"; \
		cp .env.example .env; \
		echo "$(YELLOW)⚠ Please edit .env with your API keys and run 'make docker-up' again.$(NC)"; \
		exit 1; \
	fi
	$(DOCKER_COMPOSE) up -d
	@echo "$(GREEN)✓ Containers started$(NC)"
	@echo "$(YELLOW)Open http://localhost:8501 in your browser$(NC)"

docker-down: ## Stop Docker containers
	@echo "$(BLUE)Stopping Docker containers...$(NC)"
	$(DOCKER_COMPOSE) down
	@echo "$(GREEN)✓ Containers stopped$(NC)"

docker-logs: ## View Docker logs
	$(DOCKER_COMPOSE) logs -f

docker-restart: ## Restart Docker containers
	@echo "$(BLUE)Restarting Docker containers...$(NC)"
	$(DOCKER_COMPOSE) restart
	@echo "$(GREEN)✓ Containers restarted$(NC)"

docker-shell: ## Open shell in Docker container
	$(DOCKER_COMPOSE) exec blog-writer /bin/bash

# ==================== Testing & Quality ====================

test: ## Run tests (placeholder for future tests)
	@echo "$(YELLOW)⚠ No tests configured yet$(NC)"
	# $(PYTHON) -m pytest tests/

lint: ## Run linting with flake8
	@echo "$(BLUE)Running linter...$(NC)"
	@$(PYTHON) -m flake8 src/ --max-line-length=120 --exclude=__pycache__ || echo "$(YELLOW)Install flake8: pip install flake8$(NC)"

format: ## Format code with black
	@echo "$(BLUE)Formatting code...$(NC)"
	@$(PYTHON) -m black src/ --line-length=120 || echo "$(YELLOW)Install black: pip install black$(NC)"

# ==================== Cleanup ====================

clean: ## Clean generated files and cache
	@echo "$(BLUE)Cleaning up...$(NC)"
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@echo "$(GREEN)✓ Cleanup complete$(NC)"

clean-venv: ## Remove virtual environment
	@echo "$(BLUE)Removing virtual environment...$(NC)"
	@if [ -d "$(VENV)" ]; then \
		rm -rf $(VENV); \
		echo "$(GREEN)✓ Virtual environment removed$(NC)"; \
	else \
		echo "$(YELLOW)⚠ No virtual environment found$(NC)"; \
	fi

clean-all: clean ## Clean everything including generated content (keeps venv)
	@echo "$(BLUE)Cleaning all generated content...$(NC)"
	rm -rf images/* outputs/* *.md
	@echo "$(GREEN)✓ All generated content removed$(NC)"

clean-full: clean clean-venv ## Clean everything including venv
	@echo "$(BLUE)Cleaning all generated content and venv...$(NC)"
	rm -rf images/* outputs/* *.md
	@echo "$(GREEN)✓ Full cleanup complete$(NC)"

# ==================== Utilities ====================

check-env: ## Check if .env file exists and has required keys
	@echo "$(BLUE)Checking environment...$(NC)"
	@if [ ! -f .env ]; then \
		echo "$(YELLOW)⚠ .env file not found$(NC)"; \
		exit 1; \
	fi
	@grep -q "OPENAI_API_KEY" .env && echo "$(GREEN)✓ OPENAI_API_KEY found$(NC)" || echo "$(YELLOW)⚠ OPENAI_API_KEY missing$(NC)"
	@grep -q "TAVILY_API_KEY" .env && echo "$(GREEN)✓ TAVILY_API_KEY found$(NC)" || echo "$(YELLOW)⚠ TAVILY_API_KEY missing (optional)$(NC)"
	@grep -q "GOOGLE_API_KEY" .env && echo "$(GREEN)✓ GOOGLE_API_KEY found$(NC)" || echo "$(YELLOW)⚠ GOOGLE_API_KEY missing (optional)$(NC)"

list-blogs: ## List generated blog files
	@echo "$(BLUE)Generated blogs:$(NC)"
	@ls -1 *.md 2>/dev/null | grep -v README.md || echo "$(YELLOW)No blogs found$(NC)"

# ==================== Info ====================

info: ## Show project information
	@echo "$(BLUE)Project Information$(NC)"
	@echo "Python: $$($(PYTHON) --version)"
	@echo "Pip: $$($(PIP) --version | cut -d' ' -f2)"
	@echo "Streamlit: $$($(STREAMLIT) --version 2>/dev/null | head -n1 || echo 'Not installed')"
	@echo "Docker: $$(docker --version 2>/dev/null || echo 'Not installed')"
	@echo "Docker Compose: $$(docker-compose --version 2>/dev/null || echo 'Not installed')"
	@if [ -d "$(VENV)" ]; then \
		echo "Virtual Environment: $(GREEN)Active at $(VENV)$(NC)"; \
		echo "Venv Python: $$($(VENV_PYTHON) --version 2>/dev/null || echo 'Error')"; \
	else \
		echo "Virtual Environment: $(YELLOW)Not created$(NC)"; \
	fi
