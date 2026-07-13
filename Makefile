# moai-stack — platform + always-on runtime control.
# Requires membership in the `docker` group.
# Re-login (or `newgrp docker`) after a fresh `sudo usermod -aG docker $USER`.

# Single source of truth for the LLM model. moai-stack owns ollama, so it owns
# getting PERSONA_MODEL into it. We read it straight from the same .env that
# docker compose loads, so `make` and the containers never disagree; the ?=
# below is only the fallback when .env is absent. `export` hands it to the
# persona-cli subprocess `make chat` spawns. Override at the shell to switch.
-include .env
export PERSONA_MODEL
PERSONA_MODEL ?= huihui_ai/qwen3.5-abliterated:9b
# Legacy alias for `make pull MODEL=...` / `make smoke MODEL=...` operator
# muscle memory; defaults to PERSONA_MODEL.
MODEL ?= $(PERSONA_MODEL)

# The derived runtime model is a LOCAL ollama tag: it can't be pulled, and its
# ~18 GB blob is too big to publish as an image. `build-model` creates it from
# the Modelfile; `pull-model` calls that automatically when PERSONA_MODEL is
# this tag, so every target that depends on pull-model (chat, load-persona, e2e)
# just works.
DERIVED_MODEL ?= moai-qwen3-moe
MODEL_BASE ?= huihui_ai/qwen3-abliterated:30b-a3b
MODELFILE  ?= Modelfile.moai

# voice-svc lives here and needs the host `video` group's GID for GPU access.
export VOICE_SVC_GPU_GID ?= $(shell getent group video | cut -d: -f3)

GITLAB_PYPI_CLI  ?= https://gitlab.com/api/v4/projects/83774809/packages/pypi/simple
GITLAB_PYPI_CORE ?= https://gitlab.com/api/v4/projects/83381755/packages/pypi/simple
EMBED_MODEL      ?= nomic-embed-text
E2E_DIR          ?= tests/e2e
E2E_VENV         ?= $(E2E_DIR)/.venv

# Persona chatted with by `make chat` (override: make chat PERSONA_ID=...).
PERSONA_ID ?= ada-mcleish
# Extra persona-cli flags, e.g. make chat CLI_ARGS="--no-voice --scenario shift-cut-corridor".
CLI_ARGS   ?=

# `make load-persona` reads $(PERSONA_ID).md from here and POSTs it to the store.
# Same env vars the e2e harness (helpers/config.py) uses, so overrides apply to both.
MOAI_PERSONAS_DIR ?= $(HOME)/moai/personas
PERSONA_FILE      ?= $(MOAI_PERSONAS_DIR)/$(PERSONA_ID).md
PERSONA_STORE_URL ?= http://localhost:7600

.PHONY: help up down restart logs ps pull models smoke vram chat ollama-chat ui \
        qdrant-status qdrant-ui pull-model build-model load-persona e2e

help: ## Show this help
	@grep -hE '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  %-14s %s\n", $$1, $$2}'

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

build-model: up ## Build the local derived model (moai-qwen3-moe) from Modelfile.moai; idempotent, cheap (reuses the base blob)
	@docker compose exec -T ollama ollama list | grep -qF "$(MODEL_BASE)" \
	  || { echo "[build-model] pulling base $(MODEL_BASE) (~18.6 GB, first time only)"; \
	       docker compose exec ollama ollama pull $(MODEL_BASE); }
	@echo "[build-model] creating $(DERIVED_MODEL) from $(MODELFILE)"
	docker compose cp $(MODELFILE) ollama:/tmp/$(notdir $(MODELFILE))
	docker compose exec ollama ollama create $(DERIVED_MODEL) -f /tmp/$(notdir $(MODELFILE))

pull-model: up ## Ensure PERSONA_MODEL + EMBED_MODEL are available (builds the derived model if PERSONA_MODEL is local)
	@echo "[pull-model] embed model $(EMBED_MODEL) (no-op if cached)"
	docker compose exec ollama ollama pull $(EMBED_MODEL)
	@if [ "$(PERSONA_MODEL)" = "$(DERIVED_MODEL)" ]; then \
	  echo "[pull-model] $(PERSONA_MODEL) is a local derived tag -> build-model"; \
	  $(MAKE) build-model; \
	else \
	  echo "[pull-model] pulling $(PERSONA_MODEL) (no-op if cached)"; \
	  docker compose exec ollama ollama pull $(PERSONA_MODEL); \
	fi

smoke: ## Quick inference smoke test against MODEL
	@curl -s http://localhost:11434/api/generate -d '{"model":"$(MODEL)","prompt":"In one sentence, what is the difference between an LLM and a database?","stream":false}' \
	  | python3 -c 'import sys,json;print(json.load(sys.stdin).get("response","").strip())'

vram: ## Show GPU memory usage
	@nvidia-smi --query-gpu=name,memory.used,memory.total,utilization.gpu --format=csv

chat: pull-model $(E2E_VENV)/bin/persona ## Persona chat with PERSONA_ID (override: make chat PERSONA_ID=...)
	$(E2E_VENV)/bin/persona chat $(PERSONA_ID) $(CLI_ARGS)

ollama-chat: ## Raw terminal chat with MODEL via the ollama CLI (no persona)
	docker compose exec -it ollama ollama run $(MODEL)

load-persona: pull-model $(E2E_VENV)/bin/persona ## Ingest PERSONA_ID's markdown into persona-store (make load-persona PERSONA_ID=...)
	@test -f "$(PERSONA_FILE)" || { echo "persona file not found: $(PERSONA_FILE)"; echo "set MOAI_PERSONAS_DIR or PERSONA_FILE"; exit 2; }
	@echo "[load-persona] ingesting $(PERSONA_FILE) as '$(PERSONA_ID)' into $(PERSONA_STORE_URL)"
	@PID="$(PERSONA_ID)" PF="$(PERSONA_FILE)" PERSONA_STORE_URL="$(PERSONA_STORE_URL)" PYTHONPATH="$(E2E_DIR)" \
	  $(E2E_VENV)/bin/python -c 'import os; from pathlib import Path; from persona_core.parser import parse_persona_file; from persona_core.serialization import persona_to_definition; from helpers.store_http import StoreHTTP; p = parse_persona_file(Path(os.environ["PF"])); s = StoreHTTP(os.environ["PERSONA_STORE_URL"]); s.post_persona(os.environ["PID"], persona_to_definition(p), spec_version=p.spec_version); r = s.get_runtime(os.environ["PID"]); print("loaded:", os.environ["PID"], "(http", s.get_persona(os.environ["PID"]).status_code, "memory_seeded", (r or {}).get("memory_seeded"), ")")'

ui: ## Open the chat web UI in the default browser
	@xdg-open http://localhost:8080 >/dev/null 2>&1 &

qdrant-status: ## Show Qdrant collections and health
	@curl -s http://localhost:6333/healthz && echo
	@curl -s http://localhost:6333/collections | python3 -m json.tool

qdrant-ui: ## Open Qdrant dashboard
	@echo "Qdrant dashboard: http://localhost:6333/dashboard"

# Build the harness venv holding the published persona-cli + persona-core
# wheels. Shared by `make chat` (build-once) and `make e2e` (forced rebuild).
define build_venv
python3 -m venv $(E2E_VENV)
$(E2E_VENV)/bin/pip install -q --upgrade pip
$(E2E_VENV)/bin/pip install -q --extra-index-url $(GITLAB_PYPI_CLI) --extra-index-url $(GITLAB_PYPI_CORE) -e $(E2E_DIR)
endef

# `make chat` builds this once; rebuilt only when the harness pyproject changes.
$(E2E_VENV)/bin/persona: $(E2E_DIR)/pyproject.toml
	@echo "[venv] building persona-cli harness venv (persona-cli + persona-core)"
	$(build_venv)

E2E_IMAGE_GEN_MODEL ?= realvis-xl-v5
e2e: export IMAGE_GEN_MODEL := $(E2E_IMAGE_GEN_MODEL)
e2e: up pull-model ## Run the gated end-to-end integration suite (GPU host)
	@echo "[e2e] rebuilding harness venv from pinned wheels"
	rm -rf $(E2E_VENV)
	$(build_venv)
	@echo "[e2e] waiting for HTTP services to become ready (up -d does not wait for health)"
	@for url in http://localhost:7600/health http://localhost:7000/health \
	            http://localhost:6333/healthz http://localhost:11434/api/tags \
	            http://localhost:8080/health http://localhost:7300/health \
	            http://localhost:7250/health; do \
	  printf '  %-40s ' "$$url"; \
	  n=0; until curl -fsS "$$url" >/dev/null 2>&1; do \
	    n=$$((n+1)); [ $$n -gt 60 ] && { echo "TIMEOUT"; exit 1; }; sleep 3; \
	  done; echo "ok"; \
	done
	@echo "[e2e] running pytest"
	PERSONA_MODEL="$(PERSONA_MODEL)" EMBED_MODEL="$(EMBED_MODEL)" \
	  $(E2E_VENV)/bin/python -m pytest $(E2E_DIR) -v
