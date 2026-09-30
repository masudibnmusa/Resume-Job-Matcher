import json
from typing import Any

from app import config


class LLMError(RuntimeError):
    pass


def _extract_json(text: str) -> Any:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
    starts = [i for i in (text.find("{"), text.find("[")) if i != -1]
    if not starts:
        raise ValueError("No JSON found in model output")
    start = min(starts)
    end = max(text.rfind("}"), text.rfind("]"))
    if end <= start:
        raise ValueError("Unterminated JSON in model output")
    return json.loads(text[start : end + 1])


class LLMClient:
    """Thin wrapper around the Anthropic API. Swap this file to use another provider."""

    def __init__(self, model: str | None = None, api_key: str | None = None):
        self.model = model or config.LLM_MODEL
        self.api_key = api_key or config.ANTHROPIC_API_KEY
        if not self.api_key:
            raise LLMError("ANTHROPIC_API_KEY is not set (add it to .env or run with --no-llm).")
        from anthropic import Anthropic

        self._client = Anthropic(api_key=self.api_key)

    def complete(
        self, prompt: str, system: str = "", max_tokens: int = 2000, temperature: float = 0.2
    ) -> str:
        try:
            resp = self._client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system or "You are a precise assistant.",
                messages=[{"role": "user", "content": prompt}],
            )
        except Exception as e:  # network, auth, rate limit...
            raise LLMError(f"LLM request failed: {e}") from e
        return "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")

    def complete_json(self, prompt: str, system: str = "", max_tokens: int = 3000) -> Any:
        last_err: Exception | None = None
        for attempt in range(2):
            p = prompt if attempt == 0 else prompt + "\n\nReturn ONLY valid JSON. No prose, no code fences."
            text = self.complete(p, system=system, max_tokens=max_tokens, temperature=0.0)
            try:
                return _extract_json(text)
            except ValueError as e:
                last_err = e
        raise LLMError(f"Model did not return valid JSON: {last_err}")