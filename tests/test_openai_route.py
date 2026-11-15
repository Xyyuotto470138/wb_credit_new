"""The chat-completions live route (GPT direct at OpenAI, other models through OpenRouter). Offline: the client is a stub."""
from types import SimpleNamespace

import pytest

from backend.app.llm import live
from backend.app.llm.registry import ModelEntry, load_registry, paper_model


def entry(**changes):
    fields = dict(id='gpt-test-direct', display_name='GPT test', family='gpt-test', route='direct', provider_type='openai_compatible',
        base_url='https://api.openai.com/v1', model_id='gpt-test', api_key_env='OPENAI_API_KEY',
        capabilities=dict(json_mode=False, context_size=None), enabled=True, weights='hosted', sources=['test'], verified_at='2026-11-15',
        notes='test entry', price_input_usd_per_mtok='2.00', price_output_usd_per_mtok='10.00', price_source='test rates', price_date='2026-11-15')
    return ModelEntry.model_validate(fields | changes)


class StubChat:
    def __init__(self, text='{"parts": {}}', finish='stop', refusal=None, cached=0, served='gpt-test-2026-10-01'):
        self.requests, self.reply = [], SimpleNamespace(model=served,
            choices=[SimpleNamespace(finish_reason=finish, message=SimpleNamespace(content=text, refusal=refusal))],
            usage=SimpleNamespace(prompt_tokens=1000, completion_tokens=500, prompt_tokens_details=SimpleNamespace(cached_tokens=cached)))
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    def create(self, **request):
        self.requests.append(request)
        return self.reply


@pytest.fixture
def gate(monkeypatch, tmp_path):
    monkeypatch.setenv('WB_CREDIT_LIVE', '1')
    monkeypatch.setenv('OPENAI_API_KEY', 'test-key-not-real')
    monkeypatch.setenv('WB_CREDIT_LEDGER', str(tmp_path / 'ledger.jsonl'))


def test_route_needs_the_live_flag_the_key_and_an_enabled_entry(monkeypatch, tmp_path):
    monkeypatch.setenv('WB_CREDIT_LEDGER', str(tmp_path / 'ledger.jsonl'))
    monkeypatch.delenv('WB_CREDIT_LIVE', raising=False)
    monkeypatch.setenv('OPENAI_API_KEY', 'test-key-not-real')
    assert not entry().live
    with pytest.raises(live.LiveCallError, match='Live calls are off'):
        live.provider(entry(), client=StubChat())
    monkeypatch.setenv('WB_CREDIT_LIVE', '1')
    assert entry().live and not entry(enabled=False).live and not entry(route='ollama', base_url='http://localhost').live
    with pytest.raises(live.LiveCallError, match='enabled direct or OpenRouter'):
        live.provider(entry(enabled=False), client=StubChat())
    monkeypatch.delenv('OPENAI_API_KEY')
    monkeypatch.setattr(live, 'ROOT', tmp_path)  # no .env here either
    assert not entry().live


def test_call_sends_system_and_user_text_and_records_usage_and_cost(gate):
    stub = StubChat()
    text, call = live.provider(entry(), client=stub).complete('system text', 'user text', case_id='c1', section_id=4, purpose='draft')
    assert text == '{"parts": {}}'
    assert stub.requests == [dict(model='gpt-test', messages=[dict(role='system', content='system text'), dict(role='user', content='user text')])]
    # 1,000 input tokens at USD 2 and 500 output tokens at USD 10 per million.
    assert call['cost_usd'] == '0.007000' and call['input_tokens'] == 1000 and call['output_tokens'] == 500
    assert call['route'] == 'direct' and call['requested_model'] == 'gpt-test' and call['model'] == 'gpt-test-2026-10-01'
    assert live.read_ledger() == [call]
    json_stub = StubChat()
    live.provider(entry(capabilities=dict(json_mode=True, context_size=None)), client=json_stub).complete('s', 'u', case_id='c1', section_id=4, purpose='draft')
    assert json_stub.requests[0]['response_format'] == {'type': 'json_object'}


def test_cut_off_declined_and_cached_calls_are_handled_as_on_the_anthropic_route(gate):
    for stub, message in ((StubChat(finish='length'), 'cut off'), (StubChat(refusal='I cannot help with that'), 'declined'),
                          (StubChat(finish='content_filter'), 'declined'), (StubChat(text=''), 'no text')):
        with pytest.raises(live.LiveCallError, match=message):
            live.provider(entry(), client=stub).complete('s', 'u', case_id='c1', section_id=4, purpose='draft')
    assert len(live.read_ledger()) == 4  # a failed call is still recorded
    _, cached = live.provider(entry(), client=StubChat(cached=400)).complete('s', 'u', case_id='c1', section_id=4, purpose='draft')
    assert cached['cost_usd'] is None and cached['usage']['cache_read_input_tokens'] == 400  # cached rates are not held: unpriced, never guessed
    _, other = live.provider(entry(), client=StubChat(served='another-model')).complete('s', 'u', case_id='c1', section_id=4, purpose='draft')
    assert other['cost_usd'] is None

    class Failing:
        chat = SimpleNamespace(completions=SimpleNamespace(create=lambda **request: (_ for _ in ()).throw(RuntimeError('401 invalid api key'))))
    with pytest.raises(live.LiveCallError, match='invalid api key'):
        live.provider(entry(), client=Failing()).complete('s', 'u', case_id='c1', section_id=4, purpose='draft')


def test_the_model_setting_redirects_live_papers_only(monkeypatch, tmp_path):
    registry = load_registry()
    monkeypatch.setattr(live, 'ROOT', tmp_path)
    monkeypatch.setenv('WB_CREDIT_MODEL', 'opus-5-5-direct')
    monkeypatch.delenv('WB_CREDIT_LIVE', raising=False)
    assert paper_model(registry, 'fable-5-2-direct').id == 'fable-5-2-direct'  # the setting does nothing outside a live run
    monkeypatch.setenv('WB_CREDIT_LIVE', '1')
    assert paper_model(registry, 'fable-5-2-direct').id == 'opus-5-5-direct'
    assert paper_model(registry, 'mock-v1').id == 'mock-v1'  # a paper on the mock provider stays on it
    assert paper_model(registry, 'fable-5-2-direct', requested='mock-v2').id == 'mock-v2'  # an explicit choice wins
    monkeypatch.setenv('WB_CREDIT_MODEL', 'not-in-the-registry')
    with pytest.raises(ValueError, match='Unknown registered model'):
        paper_model(registry, 'fable-5-2-direct')
