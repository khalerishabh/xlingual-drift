"""
One policy for every model: anything served behind an OpenAI-compatible
chat-completions endpoint. That covers vLLM on Colab (the real runs),
Ollama on a laptop (debugging only), and hosted APIs if they are added
later, so the model is the only thing that changes between conditions.

The system prompt is a versioned file under agent/prompts/ and is identical
across languages (Section 8.7). Thinking mode, temperature and seed come
from the config and must be held fixed across every condition being
compared.

Endpoint failures raise InfraError. Those episodes are logged but never
scored, so a flaky server cannot masquerade as an agent failure.

A completely empty reply (no text, no reasoning, no tool call) is not an
answer: it is resampled with a different seed, up to EMPTY_RESAMPLES times,
and counted in usage["empty_responses"]. Only if every resample is empty
does the episode end unbooked.
"""

import json
import os
import time
from pathlib import Path

_PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"


EMPTY_RESAMPLES = 2


class InfraError(RuntimeError):
    pass


def _render_observation(obs: dict) -> str:
    if "result" in obs:
        # ensure_ascii=False so localised text reaches the model as real
        # script rather than \u escapes, which would change the condition.
        return json.dumps(obs["result"], ensure_ascii=False)
    return obs["error"]["message"]


def _reasoning_of(message) -> str | None:
    for attr in ("reasoning_content", "reasoning"):
        value = getattr(message, attr, None)
        if value:
            return value
    return None


class OpenAICompatPolicy:
    def __init__(self, model: str, base_url: str | None = None, api_key_env: str | None = None,
                 temperature: float = 0.0, seed: int | None = None, max_tokens: int = 4096,
                 extra_body: dict | None = None, prompt_version: str = "system_v1",
                 client=None, max_retries: int = 4, retry_base_s: float = 2.0):
        self.model = model
        self.temperature = temperature
        self.seed = seed
        self.max_tokens = max_tokens
        self.extra_body = extra_body or {}
        self.prompt_version = prompt_version
        self.max_retries = max_retries
        self.retry_base_s = retry_base_s
        self.system_template = (_PROMPTS_DIR / f"{prompt_version}.txt").read_text(encoding="utf-8")
        if client is None:
            from openai import OpenAI
            api_key = os.environ.get(api_key_env, "") if api_key_env else ""
            client = OpenAI(base_url=base_url, api_key=api_key or "EMPTY", timeout=180)
        self.client = client

    def reset(self, request: str, tool_schemas: list, context: dict | None = None):
        self.tools = [{"type": "function", "function": s} for s in tool_schemas]
        self.messages = [
            {"role": "system", "content": self.system_template.format(**(context or {}))},
            {"role": "user", "content": request},
        ]
        self.reasoning = []
        self.usage = {"prompt_tokens": 0, "completion_tokens": 0, "model_calls": 0, "empty_responses": 0}
        self.finish_reasons = []
        self._consumed = 0
        self._pending_call_id = None

    def next_action(self, observations: list) -> dict:
        for obs in observations[self._consumed:]:
            self.messages.append({
                "role": "tool",
                "tool_call_id": self._pending_call_id,
                "content": _render_observation(obs),
            })
        self._consumed = len(observations)

        message = self._complete()
        for attempt in range(1, EMPTY_RESAMPLES + 1):
            if message.tool_calls or (message.content or "").strip() or _reasoning_of(message):
                break
            self.usage["empty_responses"] += 1
            message = self._complete(seed_offset=1000 * attempt)
        self.reasoning.append(_reasoning_of(message))
        calls = message.tool_calls or []

        if not calls:
            self.messages.append({"role": "assistant", "content": message.content or ""})
            return {"final": True, "text": message.content}

        # Only the first call is executed; the others are dropped from the
        # history too, so the transcript never shows calls without results.
        call = calls[0]
        name, raw_args = call.function.name, call.function.arguments or "{}"
        self._pending_call_id = call.id
        self.messages.append({
            "role": "assistant",
            "content": message.content,
            "tool_calls": [{"id": call.id, "type": "function",
                            "function": {"name": name, "arguments": raw_args}}],
        })

        try:
            args = json.loads(raw_args)
        except json.JSONDecodeError:
            args = None
        if not isinstance(args, dict):
            return {"tool": name, "parse_error": f"ValidationError: arguments for {name} must be a JSON object"}
        return {"tool": name, "args": args}

    def _complete(self, seed_offset: int = 0):
        kwargs = {
            "model": self.model,
            "messages": self.messages,
            "tools": self.tools,
            "tool_choice": "auto",
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        if self.seed is not None:
            kwargs["seed"] = self.seed + seed_offset
        if self.extra_body:
            kwargs["extra_body"] = self.extra_body

        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                response = self.client.chat.completions.create(**kwargs)
                break
            except Exception as e:
                last_error = e
                status = getattr(e, "status_code", None)
                if status is not None and 400 <= status < 500 and status not in (408, 429):
                    raise InfraError(f"{type(e).__name__} ({status}): {e}") from e
                if attempt < self.max_retries:
                    time.sleep(self.retry_base_s * (2 ** attempt))
        else:
            raise InfraError(f"{type(last_error).__name__}: {last_error}") from last_error

        usage = getattr(response, "usage", None)
        if usage is not None:
            self.usage["prompt_tokens"] += usage.prompt_tokens or 0
            self.usage["completion_tokens"] += usage.completion_tokens or 0
        self.usage["model_calls"] += 1
        self.finish_reasons.append(getattr(response.choices[0], "finish_reason", None))
        return response.choices[0].message

    def transcript(self) -> dict:
        return {
            "prompt_version": self.prompt_version,
            "messages": self.messages,
            "reasoning": self.reasoning,
            "usage": self.usage,
            "finish_reasons": self.finish_reasons,
        }
