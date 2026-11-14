import asyncio
import importlib
import json
import os
import socket

import pytest

from backend.app.llm.client import LiveProviderDisabled, MissingFixtureError, MockProvider, ProviderSettings, create_provider, request_key


def test_fixture_contract_and_no_fallback(tmp_path):
    messages=[{'role':'user','content':'SYNTHETIC DEMO DATA — fixture request'}]
    response={'text':'SYNTHETIC DEMO DATA — fixture response','stop_reason':'end_turn','content':[{'type':'text','text':'fixture'}]}
    fixture=tmp_path/'provider.json'
    fixture.write_text(json.dumps({request_key(messages):response}))
    provider=create_provider(fixture_path=fixture)
    assert provider.chat(messages)==response['text']
    raw=provider.chat_raw(messages)
    raw['content'].clear()
    assert provider.chat_raw(messages)['content']
    assert provider.usage[0]['cost_usd']=='0'
    assert provider.usage[0]['model']=='mock-v1'
    with pytest.raises(MissingFixtureError):
        provider.chat(messages,max_tokens=1)
    with pytest.raises(LiveProviderDisabled):
        create_provider(ProviderSettings(provider='openai',model='explicit-but-unapproved'))


def test_import_and_mock_boot_do_not_read_keys(monkeypatch):
    import backend.app.llm.client as client
    import backend.app.main as main
    original = type(os.environ).__getitem__
    def guarded(self, key):
        if any(token in key.upper() for token in ('KEY', 'SECRET', 'TOKEN', 'LLM_', 'ANTHROPIC', 'OPENAI')):
            raise AssertionError('Mock startup must not read provider/key settings')
        return original(self, key)
    monkeypatch.setattr(type(os.environ),'__getitem__',guarded)
    importlib.reload(client)
    importlib.reload(main)
    app=main.create_app()
    assert app.state.provider.get_provider_info()['provider']=='mock'
    assert app.state.team_config.template.team_id=='fig'


def test_health_asgi_with_injected_provider():
    from backend.app.main import create_app
    provider=MockProvider(settings=ProviderSettings(model='fixture-model'))
    app=create_app(provider=provider)
    assert app.state.provider is provider
    received=[]
    async def receive():
        return {'type':'http.request','body':b'','more_body':False}
    async def send(message):
        received.append(message)
    asyncio.run(app({'type':'http','asgi':{'version':'3.0'},'http_version':'1.1','method':'GET','scheme':'http','path':'/health','raw_path':b'/health','query_string':b'','headers':[],'server':('test',80),'client':('test',1),'root_path':''},receive,send))
    assert received[0]['status']==200
    payload=json.loads(received[1]['body'])
    assert payload['provider']['model']=='fixture-model'
    assert payload['team']=='fig'


def test_network_is_blocked():
    with pytest.raises(AssertionError,match='network'):
        socket.create_connection(('example.org',443))
    with pytest.raises(AssertionError,match='network'):
        socket.getaddrinfo('example.org',443)
