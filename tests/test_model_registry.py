"""B26 offline routes, provenance, comparison isolation and version selection."""
import json

import pytest
from sqlalchemy.orm import sessionmaker

from backend.app import schemas as s
from backend.app.database import create_database
from backend.app.llm import client
from backend.app.llm.registry import load_registry, Registry
from backend.app.main import create_app
from backend.app.services.model_comparison import CompareRequest, DefaultModelRequest, compare, set_default
from backend.app.services.versions import RedraftRequest, RevisionConflict
from test_drafting import setup, generate
from test_versions import state, versions, command, revised_valuation
from test_intake import request as asgi_request


def request(app, method, path, body=None):
    return asgi_request(app, method, path, json.dumps(body).encode() if body is not None else b'')


def comparison(service, case, sid, **options):
    st = state(service, case, sid)
    payload = dict(actor='comparison-ca', model_ids=['mock-v1', 'mock-v2'],
        expected_draft_id=st.current_draft_id, expected_revision=st.editor_revision,
        expected_input_fingerprint=st.input_fingerprint) | options
    return compare(service.repo, service.evidence.storage_root, service.templates.root,
                   case.id, sid, CompareRequest(**payload))


def test_registry_routes_and_disabled_live_models():
    registry = load_registry()
    assert [m.id for m in registry.models if m.runnable] == ['mock-v1', 'mock-v2']
    for family in ['opus-5-5', 'gpt-6-1', 'gpt-5-6', 'qwen-3-6-plus', 'qwen-3-8-max', 'kimi', 'glm']:
        entries = [m for m in registry.models if m.family == family]
        assert {m.route for m in entries} == {'direct', 'openrouter'}
        assert all(not m.enabled for m in entries)
    for model in registry.models:
        assert model.sources and model.verified_at
        if model.family.startswith('qwen'):
            assert model.bank_available
        if not model.model_id:
            assert 'TODO: confirm' in model.notes
        if model.route == 'openrouter':
            assert model.api_key_env == 'OPENROUTER_API_KEY'
    assert registry.get('qwen-3-8-max-direct').weights == 'hosted'
    assert registry.get('qwen-3-6-27b-openrouter').weights == 'open_weight'
    with pytest.raises(ValueError, match='Unknown'):
        registry.get('invented')
    raw = registry.model_dump()
    raw['models'].append(raw['models'][0])
    with pytest.raises(ValueError, match='Unique'):
        Registry.model_validate(raw)


def test_config_enabled_never_authorizes_live_calls(monkeypatch):
    # No environment value, key, local route or enabled flag can open the live gate.
    monkeypatch.setenv('APPROVED_USD', '999')
    for entry in load_registry().models:
        if entry.route == 'mock':
            continue
        with pytest.raises(client.LiveProviderDisabled, match='approved_usd'):
            entry.model_copy(update={'enabled': True}).require_runnable()


def test_case_default_and_redraft_override_preserve_history(setup, database):
    service, case = setup
    chosen = set_default(service.repo, case.id, DefaultModelRequest(actor='CA',
        model_id='mock-v2', expected_model_id='mock-v1'))
    assert chosen.default_model_id == 'mock-v2'
    draft = generate(service, case, 1)
    assert draft['model_version'].startswith('mock:mock-v2:')
    assert draft['claim_spans'][0]['provider']['registry_id'] == 'mock-v2'
    assert draft['claim_spans'][0]['provider']['validation']['rejected_claims'] == 1
    versions(service).confirm(case.id, 1, command(service, case, 1))
    before = state(service, case, 1)
    set_default(service.repo, case.id, DefaultModelRequest(actor='CA', model_id='mock-v1', expected_model_id='mock-v2'))
    assert state(service, case, 1) == before
    newer = versions(service).redraft(case.id, 1, command(service, case, 1, RedraftRequest, model_id='mock-v2'))
    assert newer['parent_id'] == draft['id'] and newer['model_version'].startswith('mock:mock-v2:')
    assert service.repo.get(s.Case, case.id).default_model_id == 'mock-v1'
    assert service.get(case.id, draft['id']) == draft
    database.commit(); database.expunge_all()
    assert service.repo.get(s.Case, case.id).default_model_id == 'mock-v1'
    assert service.get(case.id, newer['id']) == newer
    with pytest.raises(RevisionConflict, match='default changed'):
        set_default(service.repo, case.id, DefaultModelRequest(actor='CA', model_id='mock-v1', expected_model_id='mock-v2'))


@pytest.mark.parametrize('sid', [1, 2, 10, 13])
def test_same_prompt_evidence_tables_and_distinct_validated_outputs(setup, sid, tmp_path):
    service, case = setup
    before = [v.model_dump() for v in versions(service).sections(case.id)]
    original_case = service.repo.get(s.Case, case.id)
    result = comparison(service, case, sid)
    (tmp_path / f'comparison-{sid}.json').write_text(json.dumps(result))
    left, right = result['results']
    assert left['draft']['text'] != right['draft']['text']
    assert left['metrics']['unsupported_claims_rejected'] == 0
    assert right['metrics']['unsupported_claims_rejected'] == 1
    assert 'UNSUPPORTED OFFLINE TEST CLAIM' not in right['draft']['text']
    assert result['computed_tables_identical'] and result['estimated_cost_usd'] == '0'
    a, b = [item['draft']['claim_spans'][0] for item in result['results']]
    assert a['prompt_hash'] == b['prompt_hash'] == result['prompt_hash']
    assert a['provider']['evidence_hash'] == b['provider']['evidence_hash']
    assert a['computed_tables'] == b['computed_tables']
    if sid in (2, 13):
        assert result['computed_table_count'] > 0
    if sid in (2, 10, 13):
        assert a['computation_id'] == b['computation_id']
        assert left['draft']['computed_value_ids'] == right['draft']['computed_value_ids']
        assert left['draft']['computed_value_ids']
    for item in result['results']:
        assert item['metrics']['citation_coverage']['percent'] == '100.00'
        assert item['metrics']['latency_ms'] >= 0
        for src in item['draft']['claim_spans'][0]['source_register']:
            assert service.evidence.resolve(case.id, src)
    assert not service.repo.list_for_case(s.DraftVersion, case.id)
    assert [v.model_dump() for v in versions(service).sections(case.id)] == before
    assert service.repo.get(s.Case, case.id) == original_case


def test_comparison_preserves_confirmation_and_rejects_stale_tokens(setup):
    service, case = setup
    draft = generate(service, case, 8)
    versions(service).confirm(case.id, 8, command(service, case, 8))
    before = state(service, case, 8)
    result = comparison(service, case, 8)
    assert result['base_draft_id'] == draft['id']
    assert state(service, case, 8) == before
    assert service.get(case.id, draft['id']) == draft
    revised_valuation(service, case)
    with pytest.raises(RevisionConflict, match='inputs changed'):
        comparison(service, case, 8, expected_input_fingerprint=before.input_fingerprint)
    fresh = comparison(service, case, 8)
    assert fresh['evidence_hash'] != result['evidence_hash']
    assert state(service, case, 8).current_draft_id == draft['id']
    assert state(service, case, 8).readiness == 'Stale'


def test_compare_and_selection_api_guards(setup, database):
    service, case = setup
    st = state(service, case, 1)
    database.commit()
    app = create_app(sessions=sessionmaker(database.bind, expire_on_commit=False),
        storage_root=service.evidence.storage_root, template_storage_root=service.templates.root)
    status, catalog = request(app, 'GET', '/models')
    assert status == 200 and not catalog['live_calls_enabled']
    payload = dict(actor='CA', role='CA', model_ids=['mock-v1','mock-v2'], expected_draft_id=None,
        expected_revision=st.editor_revision, expected_input_fingerprint=st.input_fingerprint)
    route = f'/cases/{case.id}/sections/1/compare'
    status, result = request(app, 'POST', route, payload)
    assert status == 200 and result['computed_tables_identical']
    for changes in [dict(model_ids=['mock-v1','mock-v1']), dict(model_ids=['mock-v1','bad']),
                    dict(model_ids=['mock-v1','gpt-6-1-direct']), dict(role='Credit Head'), dict(approved_usd=10)]:
        assert request(app, 'POST', route, payload | changes)[0] == 422
    assert request(app, 'POST', route, payload | dict(expected_revision=999))[0] == 409
    choose = f'/cases/{case.id}/model'
    assert request(app, 'POST', choose, dict(actor='CA', model_id='mock-v2', expected_model_id='mock-v1'))[0] == 200
    assert request(app, 'POST', choose, dict(actor='CA', model_id='mock-v2', expected_model_id='mock-v1'))[0] == 409
    database.expire_all()
    locked = service.repo.get(s.Case, case.id).model_copy(update={'workflow_state':'Approved'})
    service.repo.save(locked); database.commit()
    assert request(app, 'POST', route, payload)[0] == 409
    assert request(app, 'POST', choose, dict(actor='CA', model_id='mock-v1', expected_model_id='mock-v2'))[0] == 409


def test_additive_case_migration(tmp_path):
    path = tmp_path/'old.sqlite'
    engine, _ = create_database(path)
    with engine.begin() as connection:
        connection.exec_driver_sql('ALTER TABLE "case" DROP COLUMN default_model_id')
    engine.dispose()
    engine, _ = create_database(path)
    with engine.connect() as connection:
        cols = {row[1]:row for row in connection.exec_driver_sql('PRAGMA table_info("case")')}
        assert cols['default_model_id'][4] == "'mock-v1'"
    engine.dispose()


def test_adapter_contracts_use_injected_transports_only():
    from types import SimpleNamespace as NS
    from backend.app.llm.adapters import OpenAICompatibleAdapter, AnthropicAdapter
    calls = []
    def complete(**kwargs):
        calls.append(kwargs)
        return NS(choices=[NS(message=NS(content='{"claims":[]}'), finish_reason='stop')])
    entry = load_registry().get('qwen-3-8-max-direct')
    adapter = OpenAICompatibleAdapter(entry, NS(chat=NS(completions=NS(create=complete))))
    assert adapter.chat([dict(role='user', content='fixture')], timeout=7) == '{"claims":[]}'
    assert calls[-1]['model'] == 'qwen3.8-max' and calls[-1]['timeout'] == 7
    assert adapter.get_provider_info()['base_url'] == entry.base_url
    def native(**kwargs):
        calls.append(kwargs)
        return NS(content=[NS(model_dump=lambda: {'type':'text', 'text':'{"claims":[]}'})], stop_reason='end_turn')
    native_adapter = AnthropicAdapter(load_registry().get('opus-5-5-direct'), NS(messages=NS(create=native)))
    assert native_adapter.chat([dict(role='system', content='rules'), dict(role='user', content='fixture')]) == '{"claims":[]}'
    assert calls[-1]['system'] == 'rules' and len(calls[-1]['messages']) == 1


@pytest.mark.slow
def test_synthesis_comparison_preserves_human_position_and_all_versions(setup):
    from test_synthesis import prerequisites
    service, case = setup
    prerequisites(service, case)
    before = service.repo.list_for_case(s.DraftVersion, case.id)
    before_states = versions(service).sections(case.id)
    assert service.repo.get(s.Case, case.id).ca_position is None
    with pytest.raises(ValueError, match='CA position'):
        comparison(service, case, 14)
    position = 'Defer the request pending evidence. This is the CA position.'
    result = comparison(service, case, 14, ca_position=position)
    for output in result['results']:
        claim = output['draft']['claim_spans'][1]
        assert claim['kind'] == 'ca_position'
        assert claim['ca_position']['text'] == position
        assert not any(g.startswith('CA position not yet stated') for g in output['draft']['gaps'])
        assert 'Property-only repayment is insufficient' in output['draft']['text']
        assert output['metrics']['citation_coverage']['percent'] == '100.00'
    assert service.repo.get(s.Case, case.id).ca_position is None
    assert service.repo.list_for_case(s.DraftVersion, case.id) == before
    assert versions(service).sections(case.id) == before_states


def test_validator_reports_each_rejection_and_empty_coverage(setup):
    from backend.app.services.model_comparison import metrics
    from test_drafting import ResponseProvider
    service, case = setup
    service.provider = ResponseProvider(json.dumps({'claims': [
        {'id':'invented', 'text':'unsupported'}, {'id':'invented-again', 'text':'unsupported'},
        {'bad': 'structure'}]}))
    draft = generate(service, case, 1)
    measured = metrics(draft)
    assert measured['unsupported_claims_rejected'] == 3
    assert measured['citation_coverage']['percent'] is None
    assert measured['citation_coverage']['total'] == 0
    assert not measured['malformed_response']
