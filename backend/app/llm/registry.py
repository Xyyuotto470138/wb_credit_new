"""Configuration-only model routes; no key reads, SDK clients or network at import."""
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from . import client

ROOT = Path(__file__).resolve().parents[3]
LIVE_BLOCK = ('Live calls are off in this process. They need an enabled direct route in config/models.yaml, its API key, '
              'and a process started for a live run (WB_CREDIT_LIVE=1). approved_usd limits apply to compare runs.')


class Capabilities(BaseModel):
    model_config = ConfigDict(extra='forbid')
    json_mode: bool | None
    context_size: int | None = Field(default=None, gt=0)


class ModelEntry(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    id: str = Field(pattern=r'^[a-z0-9][a-z0-9._-]*$')
    display_name: str = Field(min_length=1)
    family: str
    route: Literal['mock', 'direct', 'openrouter', 'ollama']
    provider_type: Literal['anthropic', 'openai_compatible']
    base_url: str | None
    model_id: str | None
    api_key_env: str | None = Field(default=None, pattern=r'^[A-Z][A-Z0-9_]*$')
    capabilities: Capabilities
    enabled: bool
    bank_available: bool = False
    weights: Literal['mock', 'hosted', 'open_weight']
    mock_profile: Literal['reviewed', 'reverse_with_rejection'] | None = None
    sources: list[str] = Field(min_length=1)
    verified_at: str
    notes: str
    price_input_usd_per_mtok: str | None = None
    price_output_usd_per_mtok: str | None = None
    price_source: str | None = None
    price_date: str | None = None

    @model_validator(mode='after')
    def validate_route(self):
        if (self.route == 'mock') != bool(self.mock_profile):
            raise ValueError('Only an explicit mock route can have a fixture profile')
        if self.route != 'mock' and self.enabled:
            if not self.model_id or not self.base_url or '{' in self.base_url:
                raise ValueError('Enabled routes require confirmed model ID and endpoint')
        return self

    @property
    def live(self):
        """A live route is callable only in a process started for a live run, with its key present."""
        from . import live
        # Claude direct at Anthropic; GPT direct at OpenAI; other models through OpenRouter.
        routed = self.route == 'direct' or (self.route == 'openrouter' and self.provider_type == 'openai_compatible')
        return self.enabled and routed and live.live_enabled() and bool(live.api_key(self.api_key_env or ''))

    @property
    def runnable(self):
        return self.enabled and (self.route == 'mock' or self.live)

    def require_runnable(self):
        if not self.enabled:
            raise ValueError('Model is disabled in config/models.yaml')
        if self.route != 'mock' and not self.live:
            raise client.LiveProviderDisabled(LIVE_BLOCK)
        return self

    def public(self):
        return self.model_dump() | dict(runnable=self.runnable,
            estimated_cost_usd='0' if self.route == 'mock' else None, live=self.live,
            blocked_reason=None if self.runnable else 'Disabled in configuration' if not self.enabled else LIVE_BLOCK)


class Registry(BaseModel):
    model_config = ConfigDict(extra='forbid')
    version: str
    default_model: str
    models: list[ModelEntry]

    @model_validator(mode='after')
    def validate_ids(self):
        ids = [m.id for m in self.models]
        if len(ids) != len(set(ids)) or self.default_model not in ids:
            raise ValueError('Unique registry IDs and a registered default are required')
        self.get(self.default_model).require_runnable()
        return self

    def get(self, model_id):
        found = next((m for m in self.models if m.id == model_id), None)
        if found is None:
            raise ValueError('Unknown registered model')
        return found


def paper_model(registry, default_id, requested=None):
    """The model a live call for a paper uses: the one asked for, else WB_CREDIT_MODEL when set, else the paper's own.
    A paper on the mock provider stays on it, so the offline demo and the tests are not redirected."""
    entry = registry.get(requested or default_id)
    from . import live
    override = live.model_override()
    if not requested and override and entry.route != 'mock':
        entry = registry.get(override)
    return entry


def load_registry(path=None):
    return Registry.model_validate(yaml.safe_load(Path(path or ROOT / 'config/models.yaml').read_text()))


def fixture_provider(entry, messages, response):
    """Reviewed fixture selection, varied without changing the shared prompt."""
    from copy import deepcopy
    import json
    entry.require_runnable()
    fixture = json.loads((ROOT / 'backend/app/fixtures/model_profiles.json').read_text())
    profile = fixture['profiles'][entry.mock_profile]
    response = deepcopy(response)
    if profile['order'] == 'reverse':
        response['claims'].reverse()
    response['claims'].extend(profile['extra_claims'])
    provider = client.MockProvider({client.request_key(messages): dict(text=json.dumps(response), stop_reason='end_turn', content=[])},
        client.ProviderSettings(model=entry.model_id, fixture_version=fixture['version']))
    return provider
