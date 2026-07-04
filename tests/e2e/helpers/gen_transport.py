"""A GenerationClient transport that calls ollama with think=False.

persona-cli's GenerationClient takes an injectable transport; the published
client calls transport.generate(model, prompt, options[, stream]). We supply a
wrapper that adds think=False when talking to the real ollama, so GP2 can
exercise the real run_turn/GenerationClient orchestration against a *published*
persona-cli without the reasoning model returning an empty response.

Trade-off: this validates the composition wiring (retrieve -> generate -> write
-> persist across services), not that the shipped persona-cli disables thinking
itself. The product-level fix (thinking off at the composition/model layer)
is tracked separately.
"""

from __future__ import annotations

from typing import Any


class NoThinkTransport:
    def __init__(self, host: str | None = None) -> None:
        import ollama

        self._client = ollama.Client(host=host) if host else ollama.Client()

    def generate(
        self,
        model: str,
        prompt: str,
        options: dict | None = None,
        stream: bool = False,
    ) -> Any:
        return self._client.generate(
            model=model,
            prompt=prompt,
            options=options,
            stream=stream,
            think=False,
        )
