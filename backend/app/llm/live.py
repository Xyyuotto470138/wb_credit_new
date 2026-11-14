"""Live model calls, behind an explicit gate, with every call recorded for cost tracking.

Gate (all three are required): the process was started with WB_CREDIT_LIVE=1 (the live run
scripts set it; tests and the mock demo never do), the registry entry is enabled, and its API
key is present in the environment or the project's .env. Keys are never logged or returned.

The project owner's decisions on live models (11 Nov 2026): Claude models go
direct to Anthropic; every live call is recorded with model, route, case, section, purpose,
tokens and cost; prices come from the provider's published rates held in config/models.yaml.
"""
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import json
import os
import threading

ROOT = Path(__file__).resolve().parents[3]
FALLBACK_BETA = 'server-side-fallback-2026-07-01'
_lock = threading.Lock()


class LiveCallError(RuntimeError):
    pass


def live_enabled():
    return os.environ.get('WB_CREDIT_LIVE') == '1'


def api_key(name):
    """Read a key from the environment, else from the project's .env. Returns None when absent."""
    if os.environ.get(name):
        return os.environ[name]
    env = ROOT / '.env'
    if env.exists():
        for line in env.read_text().splitlines():
            key, _, value = line.partition('=')
            if key.strip() == name and value.strip():
                return value.strip().strip('"').strip("'")
    return None


def ledger_path():
    return Path(os.environ.get('WB_CREDIT_LEDGER') or ROOT / 'runtime/costs/ledger.jsonl')


def record(entry):
    path = ledger_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with _lock, path.open('a') as handle:
        handle.write(json.dumps(entry, sort_keys=True) + '\n')


def read_ledger():
    path = ledger_path()
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def totals(entries=None):
    """Running totals by model, in the shape the settings page and docs/cost_log.md show."""
    result = {}
    for entry in read_ledger() if entries is None else entries:
        row = result.setdefault(entry['model'], dict(model=entry['model'], route=entry['route'], calls=0, input_tokens=0,
                                                     output_tokens=0, cost_usd=Decimal(0), unpriced_calls=0))
        row['calls'] += 1
        row['input_tokens'] += entry['input_tokens']
        row['output_tokens'] += entry['output_tokens']
        if entry['cost_usd'] is None:
            row['unpriced_calls'] += 1
        else:
            row['cost_usd'] += Decimal(entry['cost_usd'])
    return [row | dict(cost_usd=str(row['cost_usd'].quantize(Decimal('0.0001')))) for row in result.values()]


def cost_usd(entry, usage):
    """Cost from the provider's reported usage and the published rates held in the registry entry."""
    if entry.price_input_usd_per_mtok is None or entry.price_output_usd_per_mtok is None:
        return None
    if usage['cache_creation_input_tokens'] or usage['cache_read_input_tokens']:
        return None  # This build sends no cache breakpoints, so cached-token rates are not held; record as unpriced.
    rate_in, rate_out = Decimal(entry.price_input_usd_per_mtok), Decimal(entry.price_output_usd_per_mtok)
    return ((Decimal(usage['input_tokens']) * rate_in + Decimal(usage['output_tokens']) * rate_out) / Decimal(1_000_000)).quantize(Decimal('0.000001'))


class AnthropicLive:
    """Direct Anthropic route. One JSON-in-text request per call; no tools, no sampling parameters."""

    def __init__(self, entry, client=None):
        if not live_enabled():
            raise LiveCallError('Live calls are off for this process')
        if entry.provider_type != 'anthropic' or entry.route != 'direct' or not entry.enabled:
            raise LiveCallError('Only an enabled direct Anthropic route can be called in this build')
        key = api_key(entry.api_key_env)
        if not key and client is None:
            raise LiveCallError(f'{entry.api_key_env} is not set')
        if client is None:
            import anthropic
            client = anthropic.Anthropic(api_key=key, max_retries=2)
        self.entry, self.client = entry, client

    def get_provider_info(self):
        return dict(provider='anthropic', model=self.entry.model_id, registry_id=self.entry.id, route=self.entry.route)

    def complete(self, system, user, *, case_id, section_id, purpose, max_tokens=64000):
        """Return (text, call record). Raises LiveCallError when the model declines or the output is cut off."""
        started = datetime.now(timezone.utc)
        with self.client.beta.messages.stream(model=self.entry.model_id, max_tokens=max_tokens, system=system,
                                              messages=[{'role': 'user', 'content': user}],
                                              betas=[FALLBACK_BETA], fallbacks='default') as stream:
            message = stream.get_final_message()
        usage = dict(input_tokens=message.usage.input_tokens or 0, output_tokens=message.usage.output_tokens or 0,
                     cache_creation_input_tokens=getattr(message.usage, 'cache_creation_input_tokens', 0) or 0,
                     cache_read_input_tokens=getattr(message.usage, 'cache_read_input_tokens', 0) or 0)
        served_by = message.model
        # A fallback model has its own published rates; without them here the call is recorded as unpriced, never guessed.
        cost = cost_usd(self.entry, usage) if served_by == self.entry.model_id else None
        entry = dict(at=started.isoformat(), seconds=round((datetime.now(timezone.utc) - started).total_seconds(), 1),
                     model=served_by, requested_model=self.entry.model_id, registry_id=self.entry.id, route=self.entry.route,
                     case_id=case_id, section_id=section_id, purpose=purpose, stop_reason=message.stop_reason,
                     input_tokens=usage['input_tokens'] + usage['cache_creation_input_tokens'] + usage['cache_read_input_tokens'],
                     output_tokens=usage['output_tokens'], usage=usage, cost_usd=None if cost is None else str(cost),
                     price_basis=None if cost is None else f'{self.entry.price_source}, {self.entry.price_date}')
        record(entry)
        if message.stop_reason == 'refusal':
            raise LiveCallError('The model declined this request')
        if message.stop_reason == 'max_tokens':
            raise LiveCallError('The model response was cut off at the output limit')
        return ''.join(block.text for block in message.content if block.type == 'text'), entry
