# moai-stack — platform + always-on runtime control.
# Requires membership in the `docker` group.
# Re-login (or `newgrp docker`) after a fresh `sudo usermod -aG docker $USER`.

# Single source of truth for the LLM model — moai-stack owns ollama, so it owns
# getting PERSONA_MODEL into it. persona-web (authoring repo) reads the same
# value from its own .env. Override at the shell or in .env to switch.
PERSONA_MODEL ?= huihui_ai/qwen3.5-abliterated:9b
# Legacy alias for `make pull MODEL=...` / `make smoke MODEL=...` operator
# muscle memory; defaults to PERSONA_MODEL.
MODEL ?= $(PERSONA_MODEL)

# voice-svc lives here and needs the host `video` group's GID for GPU access.
export VOICE_SVC_GPU_GID ?= $(shell getent group video | cut -d: -f3)

.PHONY: help up down restart logs ps pull models smoke vram chat ui \
        qdrant-status qdrant-ui pull-model

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  %-14s %s\n", $$1, $$2}'

up: ## Start the platform + runtime services in the background
	docker compose up -d

down: ## Stop and remove services (named volumes preserved)
	docker compose down

restart: ## Restart the ollama service
	docker compose restart ollama

logs: ## Tail ollama logs
	docker compose logs -f ollama

ps: ## Show service status
	docker compose ps

pull: ## Pull MODEL (override: make pull MODEL=...)
	docker compose exec ollama ollama pull $(MODEL)

models: ## List downloaded models
	docker compose exec ollama ollama list

pull-model: up ## Pull PERSONA_MODEL into ollama (~6.6 GB; idempotent)
	@echo "[pull-model] pulling $(PERSONA_MODEL) (no-op if already cached)"
	docker compose exec ollama ollama pull $(PERSONA_MODEL)

smoke: ## Quick inference smoke test against MODEL
	@curl -s http://localhost:11434/api/generate -d '{"model":"$(MODEL)","prompt":"In one sentence, what is the difference between an LLM and a database?","stream":false}' \
	  | python3 -c 'import sys,json;print(json.load(sys.stdin).get("response","").strip())'

vram: ## Show GPU memory usage
	@nvidia-smi --query-gpu=name,memory.used,memory.total,utilization.gpu --format=csv

chat: ## Terminal chat with MODEL via the ollama CLI
	docker compose exec -it ollama ollama run $(MODEL)

ui: ## Open the chat web UI in the default browser
	@xdg-open http://localhost:8080 >/dev/null 2>&1 &

qdrant-status: ## Show Qdrant collections and health
	@curl -s http://localhost:6333/healthz && echo
	@curl -s http://localhost:6333/collections | python3 -m json.tool

qdrant-ui: ## Open Qdrant dashboard
	@echo "Qdrant dashboard: http://localhost:6333/dashboard"
