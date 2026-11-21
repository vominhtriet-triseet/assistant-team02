"""Optional language-model extraction for requests the rule-based parser cannot read.

Nothing here runs unless ASSISTANT_LLM is set. Two providers are supported:

- ``ollama``: a local model served by Ollama (no API key, data stays on the machine).
- ``openai``: any OpenAI-compatible Chat Completions endpoint (OpenAI, Groq,
  OpenRouter, LM Studio, Google Gemini's OpenAI-compatible endpoint, ...).

The model only proposes structured data. The service validates every field before use
and falls back to the rule-based result when the call fails.
"""
from __future__ import annotations

import json
import os
import threading
import urllib.error
import urllib.request
from datetime import date

from assistant import REPO_ROOT

SYSTEM_PROMPT = """You extract study tasks from a student's message, written in Vietnamese or English.
Reply with JSON only, using this shape:
{"tasks": [{"title": str, "kind": "exam|quiz|assignment|project|presentation|reading|review|other",
            "deadline": "YYYY-MM-DD" or null, "hours": number or null}],
 "hours_per_day": number or null}
Rules: include only tasks the student mentioned. Use null for anything not stated.
Never invent deadlines or durations. Resolve relative dates from the given today date.
Keep each title short and in the student's own language."""

STUDY_PROMPT = """You help a student practise. Use only the material given; if no material is given,
use well-established textbook knowledge and keep it basic. Reply with JSON only:
{"summary": str (2-3 sentences), "questions": [{"question": str, "answer": str (a short answer)}]}
Write exactly 3 short questions. Write everything in {language}."""

GRADE_PROMPT = """You grade a student's answer to a practice question. Accept answers with the same
meaning, small typos, or missing accents. Reply with JSON only:
{"correct": true or false, "feedback": str (one short sentence in {language})}"""

LANGUAGES = {"vi": "Vietnamese", "en": "English"}
# One model call at a time: a single GPU serves every visitor, so requests queue instead of thrashing VRAM.
_GPU = threading.Semaphore(1)


class LLMError(RuntimeError):
    pass


def _load_dotenv() -> None:
    """Read KEY=VALUE lines from .env in the repository root without overriding real variables."""
    path = REPO_ROOT / ".env"
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        key, sep, value = line.partition("=")
        if sep and key.strip() and not key.strip().startswith("#"):
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _post_json(url: str, payload: dict, headers: dict[str, str], timeout: float) -> dict:
    request = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json", **headers}
    )
    try:
        with _GPU, urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise LLMError(f"Could not reach the language model: {exc}") from exc


class OllamaProvider:
    name = "ollama"

    def __init__(self) -> None:
        self.host = os.environ.get("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
        self.model = os.environ.get("ASSISTANT_LLM_MODEL", "qwen3:14b")

    def complete_json(self, system: str, user: str, timeout: float = 120) -> dict:
        payload = {
            "model": self.model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "stream": False,
            "format": "json",
            "think": False,  # Qwen3 answers directly; no hidden reasoning tokens before the JSON
            "keep_alive": "30m",  # keep the model in VRAM between messages
            "options": {"temperature": 0},
        }
        data = _post_json(f"{self.host}/api/chat", payload, {}, timeout)
        return _parse_content(data.get("message", {}).get("content", ""))


class OpenAICompatibleProvider:
    name = "openai"

    def __init__(self) -> None:
        self.base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
        self.api_key = os.environ.get("OPENAI_API_KEY", "")
        self.model = os.environ.get("ASSISTANT_LLM_MODEL", "")
        if not self.api_key or not self.model:
            raise LLMError("Set OPENAI_API_KEY and ASSISTANT_LLM_MODEL to use the openai provider.")

    def complete_json(self, system: str, user: str, timeout: float = 120) -> dict:
        payload = {
            "model": self.model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "temperature": 0,
            "response_format": {"type": "json_object"},
        }
        data = _post_json(f"{self.base_url}/chat/completions", payload, {"Authorization": f"Bearer {self.api_key}"}, timeout)
        try:
            return _parse_content(data["choices"][0]["message"]["content"])
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError("The language model returned an unexpected response.") from exc


def _parse_content(content: str) -> dict:
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as exc:
        raise LLMError("The language model did not return JSON.") from exc
    if not isinstance(parsed, dict):
        raise LLMError("The language model did not return a JSON object.")
    return parsed


PROVIDERS = {"ollama": OllamaProvider, "openai": OpenAICompatibleProvider}


def get_provider():
    """Return the configured provider, or None when ASSISTANT_LLM is unset."""
    _load_dotenv()
    choice = os.environ.get("ASSISTANT_LLM", "").strip().lower()
    if not choice or choice == "none":
        return None
    if choice not in PROVIDERS:
        raise LLMError(f"Unknown ASSISTANT_LLM value {choice!r}. Use ollama, openai, or leave it empty.")
    return PROVIDERS[choice]()


def extract_plan(provider, text: str, today: date) -> dict:
    user = f"Today is {today.isoformat()} ({today.strftime('%A')}).\nStudent message: {text}"
    return provider.complete_json(SYSTEM_PROMPT, user)


def study_pack(provider, topic: str, material: str, lang: str) -> dict:
    system = STUDY_PROMPT.replace("{language}", LANGUAGES[lang])
    user = f"Topic: {topic}\nMaterial:\n{material[:6000] or '(none)'}"
    return provider.complete_json(system, user)


def grade(provider, question: str, expected: str, reply: str, lang: str) -> dict:
    system = GRADE_PROMPT.replace("{language}", LANGUAGES[lang])
    user = f"Question: {question}\nExpected answer: {expected}\nStudent answer: {reply[:500]}"
    return provider.complete_json(system, user)
