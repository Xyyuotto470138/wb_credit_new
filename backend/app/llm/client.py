"""chat/chat_raw contracts adapted from Phase 1 backend/app/llm/client.py,
2026-11-10. Live adapters, environment reads and import-time clients removed.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from typing import Protocol

from pydantic import BaseModel, ConfigDict


class Provider(Protocol):
    def chat(self, messages: list[dict], max_tokens: int = 2000, temperature: float = 0, timeout: int | None = None) -> str: ...
    def chat_raw(self, messages: list[dict], max_tokens: int = 2000, temperature: float = 0, timeout: int | None = None) -> dict: ...
    def get_provider_info(self) -> dict: ...


class ProviderSettings(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    provider: str = 'mock'
    model: str = 'mock-v1'
    config_version: str = '1'
    fixture_version: str = '1'


class MissingFixtureError(LookupError):
    pass


class LiveProviderDisabled(RuntimeError):
    pass


def request_key(messages, max_tokens=2000, temperature=0, timeout=None):
    request = dict(messages=messages, max_tokens=max_tokens, temperature=temperature, timeout=timeout)
    return hashlib.sha256(json.dumps(request, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


class MockProvider:
    def __init__(self, fixtures=None, settings=None):
        self.settings = settings or ProviderSettings()
        self.fixtures = deepcopy(fixtures or {})
        self.usage = []

    def get_provider_info(self):
        return self.settings.model_dump()

    def chat_raw(self, messages, max_tokens=2000, temperature=0, timeout=None):
        key = request_key(messages, max_tokens, temperature, timeout)
        if key not in self.fixtures:
            raise MissingFixtureError(f'Missing mock fixture: {key}; no live fallback')
        result = deepcopy(self.fixtures[key])
        if not isinstance(result, dict) or not isinstance(result.get('text'), str) or 'stop_reason' not in result or 'content' not in result:
            raise ValueError('Mock response must contain text, stop_reason and content')
        self.usage.append({**self.get_provider_info(), 'request_hash': key, 'cost_usd': '0'})
        return result

    def chat(self, messages, max_tokens=2000, temperature=0, timeout=None):
        return self.chat_raw(messages, max_tokens, temperature, timeout)['text']


def create_provider(settings=None, fixture_path: Path | None = None):
    settings = settings or ProviderSettings()
    if settings.provider != 'mock':
        raise LiveProviderDisabled('Live adapters are unavailable until an approved paid-run task implements provider selection and spend limits')
    fixtures = json.loads(fixture_path.read_text()) if fixture_path else {}
    return MockProvider(fixtures, settings)


def clean_json_response(text: str) -> str:
    """Phase 1 fence cleaner, retained without model/environment side effects."""
    text = text.strip()
    if text.startswith('```json'):
        text = text[7:]
    elif text.startswith('```'):
        text = text[3:]
    if text.endswith('```'):
        text = text[:-3]
    return text.strip()
