# moai-stack

The composition layer for the persona platform: the `docker-compose.yml` +
`Makefile` + env that wire the published images into a running system. This is
**the** composition — when `persona-create` later publishes an image it re-enters
here as one more service block, no structural change.

Runtime-only. All services are external images (no build contexts):

| Service | Port | Role |
|---------|------|------|
| `ollama` | 11434 | LLM inference (GPU) |
| `open-webui` | 8080 | chat UI over ollama |
| `qdrant` | 6333/6334 | episodic memory (single multi-tenant `persona_memory` collection) |
| `postgres` | 5432 | cold-path store DB |
| `persona-store` | 7600 | persona definitions / runtime state / scenarios (`ghcr.io/muxu-io/persona-store`) |
| `voice-svc` | 7000 | runtime TTS (GPU, ~2GB) |

The compose project name is `moai`, so managed volumes keep their `moai_*`
names and existing data attaches with no migration. `ollama` and `qdrant-data`
are `external: true`.

## Run

    cp .env.sample .env        # edit POSTGRES_PASSWORD / PERSONA_MODEL as needed
    make up                    # start everything
    make pull-model            # pull PERSONA_MODEL + embed model into ollama (~6.6 GB, idempotent)
    make ps                    # status
    make down                  # stop (volumes preserved)

`make help` lists every target.

## Talk to a persona

`make chat` runs the persona CLI against a persona already loaded in
`persona-store`. It brings the stack up, pulls the models, and builds the CLI
venv as needed, then drops you into an interactive session:

    make load-persona PERSONA_ID=ada-mcleish   # ingest ~/moai/personas/ada-mcleish.md into the store
    make chat PERSONA_ID=ada-mcleish           # chat with her (PERSONA_ID defaults to ada-mcleish)

`load-persona` is a one-time step per persona — the CLI is read-only and won't
create one. Pass extra CLI flags via `CLI_ARGS`, e.g.
`make chat CLI_ARGS="--no-voice --scenario shift-cut-corridor"`. Override the
source directory with `MOAI_PERSONAS_DIR`. For raw model chat with no persona,
use `make ollama-chat`.

## Authoring services

The authoring surface (`persona-web`, `scenes-svc`, `avatar-gen`,
`voice-design-svc`, `image-gen-svc`) lives in a separate repo whose compose
attaches to the `moai` network declared here. **Start moai-stack first** — the
authoring compose hard-depends on this platform being up.

## GPU note

`voice-svc` (~2GB) here and the authoring `voice-design-svc` (~5GB) collide on
tight cards. The authoring repo's `make up`/`make down` pause and restore
`voice-svc` by container name; don't hand-juggle them.

License: Apache-2.0.
