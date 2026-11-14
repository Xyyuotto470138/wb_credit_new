"""B24 actual-pack chat, exact proposals and Python operand acceptance, offline."""
import json
from decimal import Decimal
from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from backend.app import schemas as s
from backend.app.main import create_app
from backend.app.services.section_chat import SectionChatService, ChatRequest, Decision, accepted_inputs
from backend.app.services.versions import RevisionConflict, RedraftRequest
from backend.app.llm import client as llm
from backend.app.llm.client import MockProvider
from test_drafting import setup, generate, ResponseProvider
from test_synthesis import prerequisites
from test_versions import command, state, versions, revised_valuation, edit
from test_intake import request, make_case


def chat(service, provider=None):
    return SectionChatService(service.repo, service.evidence.storage_root, service.templates.root, provider)


def propose(service, case, sid, **kw):
    return chat(service).propose(case.id, sid, command(service, case, sid, ChatRequest,
        message=kw.pop('message', 'Legal review remains pending.'), **kw))


def decide(service, case, proposal, action='accept', **kw):
    return chat(service).decide(case.id, proposal.section_id, proposal.id, Decision(actor='reviewer-ca', action=action, **kw))


def occupancy(**changes):
    return dict(metric_id='occupancy', period='2025', scope='Group', basis='comparable lettable area',
        synthetic=True, operands={'occupied_area':[dict(value='50',unit='sqm')],
                                  'lettable_area':[dict(value='80',unit='sqm')]}) | changes


@pytest.mark.slow
def test_all_sections_proposals_accept_reject_preserve_sources_and_position(setup, database):
    service, case = setup
    originals = prerequisites(service, case)
    originals[14] = generate(service, case, 14, ca_position='Defer pending evidence.')
    # Reverse order avoids intentionally invalidating a prerequisite before its dependent chat.
    for sid in (14, 11, 9, 13, 12, 10, 8, 7, 6, 5, 4, 3, 2, 1):
        old = originals[sid]
        versions(service).confirm(case.id, sid, command(service, case, sid))
        token = state(service, case, sid)
        proposal = propose(service, case, sid)
        assert state(service, case, sid) == token
        assert service.get(case.id, old['id']) == old
        assert proposal.status == 'pending'
        assert 'CA input (verbatim' in proposal.proposed_text
        rejected = decide(service, case, proposal, 'reject')
        assert rejected.status == 'rejected'
        assert state(service, case, sid) == token
        proposal = propose(service, case, sid)
        accepted = decide(service, case, proposal)
        new = service.get(case.id, accepted.accepted_draft_id)
        assert new['parent_id'] == old['id'] and new['template_version_id'] == old['template_version_id']
        assert new['text'] == proposal.proposed_text
        assert new['computed_value_ids'] == old['computed_value_ids']
        assert new['document_ids'] == old['document_ids']
        assert set(old['gaps']) <= set(new['gaps'])
        assert state(service, case, sid).confirmed_draft_id is None
        assert state(service, case, sid).readiness == 'Drafted'
        assert new['claim_spans'][0]['computed_tables'] == old['claim_spans'][0]['computed_tables']
        for claim in old['claim_spans'][1:]:
            assert claim['text'] in new['text']
        ca = service.repo.get(s.CAInput, new['ca_input_ids'][0])
        ref = next(c['evidence_ids'][0] for c in new['claim_spans'][1:] if c.get('ca_input_id') == ca.id)
        source = service.evidence.resolve(case.id, ref)
        assert source['current'] and source['page'] is None and source['document_id'] is None
        assert source['actor'] == 'editor-ca' and source['message_id'] == proposal.message_id
        assert source['origin'] == 'CA input' and source['recorded_at'] in new['text']
        versions(service).confirm(case.id, sid, command(service, case, sid))
        with pytest.raises(RevisionConflict): decide(service, case, proposal)
    assert service.repo.get(s.Case, case.id).ca_position == 'Defer pending evidence.'
    database.commit(); database.expunge_all()
    assert len(chat(service).history(case.id, 1)['proposals']) == 2


def test_numeric_preview_accept_recompute_supersession_and_redraft(setup, database):
    service, case = setup
    originals = prerequisites(service, case, 11)
    originals[11] = generate(service, case, 11)
    ten = originals[10]
    values_before = service.repo.list_for_case(s.ComputedValue, case.id)
    proposal = propose(service, case, 10, mode='numeric', numeric=occupancy())
    assert Decimal(proposal.payload['results'][0]['value']) == Decimal('62.5')
    assert service.repo.list_for_case(s.ComputedValue, case.id) == values_before
    with pytest.raises(ValueError, match='Explicit acceptance'):
        decide(service, case, proposal)
    accepted = decide(service, case, proposal, accept_numeric_input=True)
    new = service.get(case.id, accepted.accepted_draft_id)
    assert new['text'] == proposal.proposed_text
    value = next(c['value'] for c in new['claim_spans'][1:] if c.get('ca_input_id'))
    assert Decimal(value['value']) == Decimal('62.5') and value['synthetic']
    assert {k: Decimal(v) for k,v in value['operands'].items()} == {'occupied_area.0':50, 'lettable_area.0':80}
    assert service.repo.get(s.ComputedValue, value['id']).model_dump(mode='json') == value
    assert state(service, case, 9).readiness == state(service, case, 11).readiness == 'Stale'
    assert service.get(case.id, ten['id']) == ten
    assert all(service.repo.get(s.ComputedValue, v.id) == v for v in values_before)
    old_input = accepted_inputs(service.repo, case.id, 10)[0]
    revised = occupancy(operands={'occupied_area':[dict(value='40', unit='sqm')], 'lettable_area':[dict(value='80',unit='sqm')]})
    next_proposal = propose(service, case, 10, mode='numeric', numeric=revised)
    next_accept = decide(service, case, next_proposal, accept_numeric_input=True)
    active = accepted_inputs(service.repo, case.id, 10)[0]
    assert active.supersedes_id == old_input.id and active.revision == 2
    old_ref = next(iter(value['operand_evidence_ids'].values()))[0]
    assert not service.evidence.resolve(case.id, old_ref)['current']
    latest = service.get(case.id, next_accept.accepted_draft_id)
    assert '50.000000 percent' in latest['text'] and '62.500000 percent' not in latest['text']
    redraft = versions(service).redraft(case.id, 10, command(service, case, 10, RedraftRequest))
    assert '50.000000 percent' in redraft['text'] and active.id in redraft['ca_input_ids']
    versions(service).redraft(case.id, 9, command(service, case, 9, RedraftRequest))
    eleven = versions(service).redraft(case.id, 11, command(service, case, 11, RedraftRequest))
    assert '50.000000 percent' in eleven['text'] and 'CA input;' in eleven['text']
    database.commit(); database.expunge_all()
    assert service.get(case.id, next_accept.accepted_draft_id) == latest


@pytest.mark.parametrize('operands, fragment', [
    ({}, 'Missing operands'),
    ({'occupied_area':[dict(value='40',unit='sqm')], 'lettable_area':[dict(value='0',unit='sqm')]}, 'denominator'),
    ({'occupied_area':[dict(value='90',unit='sqm')], 'lettable_area':[dict(value='80',unit='sqm')]}, 'range'),
    ({'occupied_area':[dict(value='40',unit='years')], 'lettable_area':[dict(value='80',unit='sqm')]}, 'unit'),
])
def test_invalid_operands_are_gaps_never_fabricated_results(setup, operands, fragment):
    service, case = setup
    generate(service, case, 10)
    p = propose(service, case, 10, mode='numeric', numeric=occupancy(operands=operands))
    assert p.payload['results'][0]['value'] is None
    assert fragment.lower() in ' '.join(p.payload['numeric_gaps']).lower()
    accepted = decide(service, case, p, accept_numeric_input=True)
    draft = service.get(case.id, accepted.accepted_draft_id)
    assert not any(c.get('computed_value_id') for c in draft['claim_spans'][1:] if c.get('ca_input_id'))
    assert any(c.get('ca_input_id') and c['evidence_ids'] for c in draft['claim_spans'][1:])
    assert fragment.lower() in ' '.join(draft['gaps']).lower()


@pytest.mark.parametrize('payload', ['{bad', '{}', '{"operation":"append_verbatim_ca_input", "text":"SGD 999 million approved"}',
    '{"operation":"preview_python_recompute"}', '{"operation":"append_verbatim_ca_input", "evidence_ids":["invented"]}'])
def test_model_cannot_smuggle_claims_numbers_citations_or_wrong_operation(setup, payload):
    service, case = setup
    draft = generate(service, case, 8)
    with pytest.raises(ValueError):
        chat(service, ResponseProvider(payload)).propose(case.id, 8, command(service, case, 8, ChatRequest, message='Legal review remains pending.'))
    assert service.get(case.id, draft['id']) == draft
    assert not service.repo.list_for_case(s.ChatMessage, case.id)


def test_missing_fixture_no_live_calls_and_context(setup):
    service, case = setup
    draft = generate(service, case, 2)
    cmd = command(service, case, 2, ChatRequest, message='Emphasize exceptions.', mode='emphasize', claim_id=draft['claim_spans'][1]['id'])
    with pytest.raises(ValueError, match='no live fallback'):
        chat(service, MockProvider()).propose(case.id, 2, cmd)
    provider = ResponseProvider(lambda messages: json.dumps({'operation':'emphasize_existing_claim'}))
    def respond(messages):
        context = json.loads(messages[1]['content'])
        assert context['current_text'] == draft['text'] and context['sources'] and context['computed_values']
        assert context['gaps'] == draft['gaps']
        return '{"operation":"emphasize_existing_claim"}'
    provider.response = respond
    p = chat(service, provider).propose(case.id, 2, cmd)
    assert p.payload['fixture_version'] and p.payload['prompt_hash']
    assert not service.repo.list_for_case(s.CAInput, case.id)
    provider.get_provider_info = lambda: {'provider':'live'}
    with pytest.raises(llm.LiveProviderDisabled): chat(service, provider).propose(case.id, 2, cmd)


@pytest.mark.parametrize('change', ['edit', 'late', 'confirm'])
def test_stale_proposal_cannot_overwrite(setup, change):
    service, case = setup
    old = generate(service, case, 8)
    p = propose(service, case, 8)
    if change == 'edit': edit(service, case, 8, old)
    if change == 'late': revised_valuation(service, case)
    if change == 'confirm': versions(service).confirm(case.id, 8, command(service, case, 8))
    with pytest.raises(RevisionConflict): decide(service, case, p)
    assert chat(service).history(case.id, 8)['proposals'][0].status == 'stale'
    assert not accepted_inputs(service.repo, case.id)


@pytest.mark.parametrize('workflow', ['Submitted to Credit Head', 'Supported', 'With Credit Approver', 'Returned to CA',
    'Question to CA', 'Approved', 'Approved with conditions', 'Declined'])
def test_workflow_locks_apply_to_proposal_and_decisions(setup, workflow):
    service, case = setup
    generate(service, case, 8)
    p = propose(service, case, 8)
    cmd = command(service, case, 8, ChatRequest, message='Pending review.')
    case.workflow_state = workflow; service.repo.save(case)
    with pytest.raises(RevisionConflict): chat(service).propose(case.id, 8, cmd)
    for action in ('accept','reject'):
        with pytest.raises(RevisionConflict): decide(service, case, p, action)


def test_api_races_role_scope_rollback_and_persistence(setup, database):
    service, case = setup
    generate(service, case, 8)
    cmd = command(service, case, 8, ChatRequest, message='Legal review remains pending.')
    database.commit()
    sessions = sessionmaker(bind=database.bind)
    def app(provider=None):
        return create_app(sessions=sessions, storage_root=service.evidence.storage_root,
            template_storage_root=service.templates.root, chat_provider=provider)
    path = f'/cases/{case.id}/sections/8/chat'
    code, p = request(app(), 'POST', path, cmd.model_dump_json().encode())
    assert code == 200
    endpoint = path+f'/{p["id"]}/decision'
    def call(): return request(app(), 'POST', endpoint, b'{"actor":"ca","action":"accept"}')
    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses = [code for code, _ in pool.map(lambda _:call(), range(2))]
    assert sorted(statuses) == [200,409]
    code, history = request(app(), 'GET', path)
    assert code == 200 and history['proposals'][0]['status'] == 'accepted'
    assert request(app(), 'POST', endpoint, b'{"actor":"head","role":"Credit Head","action":"reject"}')[0] == 422
    database.expire_all()
    other = make_case(service.repo, borrower_name='Another demo'); database.commit()
    assert request(app(), 'POST', endpoint.replace(case.id, other.id), b'{"actor":"ca","action":"accept"}')[0] == 422
    assert request(app(), 'POST', endpoint.replace('/sections/8/', '/sections/7/'), b'{"actor":"ca","action":"accept"}')[0] == 422
    fresh = command(service, case, 8, ChatRequest, message='More review requested.')
    database.commit()
    assert request(app(ResponseProvider('{}')), 'POST', path, fresh.model_dump_json().encode())[0] == 422
    assert len(request(app(), 'GET', path)[1]['messages']) == 1


def test_numeric_guards_and_immutable_proposal(setup, database):
    service, case = setup
    generate(service, case, 8)
    for message in ('Exposure is 999 million.', 'Exposure is one million.'):
        with pytest.raises(ValueError, match='numeric operands'): propose(service, case, 8, message=message)
    with pytest.raises(ValueError, match='section 10'): propose(service, case, 8, mode='numeric', numeric=occupancy())
    p = propose(service, case, 8)
    corrupted = p.model_copy(update={'proposed_text':'unsupported'})
    with pytest.raises(ValueError, match='immutable'): service.repo.save(corrupted)
    database.commit()
    with pytest.raises(IntegrityError):
        database.execute(text('UPDATE section_proposal SET proposed_text=:text WHERE id=:id'), {'text':'bad','id':p.id})
    database.rollback()
    decide(service, case, p, 'reject'); database.commit()
    with pytest.raises(IntegrityError):
        database.execute(text("UPDATE section_proposal SET status='pending' WHERE id=:id"), {'id':p.id})
    database.rollback()


def test_emphasis_preserves_claims_and_cites_accepted_fact_in_exports(setup, tmp_path):
    from test_exports import service_for, export, text as document_text
    service, case = setup
    old = generate(service, case, 8)
    target = old['claim_spans'][-1]['id']
    proposal = propose(service, case, 8, mode='emphasize', claim_id=target, message='Emphasize the security evidence.')
    accepted = decide(service, case, proposal)
    revised = service.get(case.id, accepted.accepted_draft_id)
    assert revised['claim_spans'][1]['id'] == target
    assert {c['id'] for c in revised['claim_spans'][1:]} == {c['id'] for c in old['claim_spans'][1:]}
    assert not revised['ca_input_ids']
    fact = propose(service, case, 8, message='SYNTHETIC DEMO DATA — The valuer requested further inspection.')
    accepted = decide(service, case, fact)
    draft = service.get(case.id, accepted.accepted_draft_id)
    ca_claim = draft['claim_spans'][-1]
    ref = ca_claim['evidence_ids'][0]
    source = draft['claim_spans'][0]['source_register'][ref]
    exports, _ = service_for(setup, tmp_path)
    artifact = export(exports, case)
    body, appendix = document_text(exports.content(case.id, artifact.id)).split('\nSources\n', 1)
    marker = next(n for n, evidence in artifact.manifest['source_markers'].items() if evidence == ref)
    assert f'[{marker}]' in body and ca_claim['text'] in body
    entry = next(line for line in appendix.splitlines() if line.startswith(f'[{marker}] '))
    assert 'Credit Analyst' in entry and source['message_id'] not in entry
    assert artifact.manifest['sources'][ref]['actor'] == source['actor']
    assert artifact.manifest['sources'][ref]['message_id'] == source['message_id']
    assert __import__('backend.app.exports.formatting', fromlist=['human_date']).human_date(source['recorded_at']) in entry and f"revision {source['revision']}" in entry
    assert 'CA input' in entry and 'SYNTHETIC' in entry and 'pNone' not in entry
    redraft = versions(service).redraft(case.id, 8, command(service, case, 8, RedraftRequest))
    assert ca_claim['text'] in redraft['text'] and source['ca_input_id'] in redraft['ca_input_ids']


def test_numeric_thresholds_are_python_and_model_cannot_change_them(setup):
    service, case = setup
    generate(service, case, 10)
    supplied = dict(metric_id='aggregate_leverage', period='2026-11-11', scope='Group',
        basis='MAS Appendix 6 reported', synthetic=True,
        operands={'regulatory_leverage':[dict(value='51',unit='percent')]})
    proposal = propose(service, case, 10, mode='numeric', numeric=supplied)
    assert Decimal(proposal.payload['results'][1]['value']) == -1
    accepted = decide(service, case, proposal, accept_numeric_input=True)
    draft = service.get(case.id, accepted.accepted_draft_id)
    assert '-1.000000 percentage points' in draft['text']
    assert 'outside configured threshold' == proposal.payload['results'][0]['thresholds'][0]['status']
    ref = next(c['computed_value_id'] for c in draft['claim_spans'][1:] if c.get('ca_input_id') and c['value']['metric']=='aggregate_leverage')
    assert service.repo.get(s.ComputedValue, ref).synthetic


def test_corrupt_source_cannot_be_accepted_and_unknown_metric_rolls_back(setup, database):
    service, case = setup
    generate(service, case, 8)
    p = propose(service, case, 8)
    doc = service.repo.get(s.Document, service.repo.get(s.DraftVersion, p.base_draft_id).document_ids[0])
    path = service.evidence.storage_root / doc.storage_path
    original = path.read_bytes()
    try:
        path.write_bytes(b'changed source')
        with pytest.raises(ValueError): decide(service, case, p)
    finally:
        path.write_bytes(original)
    generate(service, case, 10)
    database.commit()
    app = create_app(sessions=sessionmaker(bind=database.bind), storage_root=service.evidence.storage_root,
        template_storage_root=service.templates.root)
    cmd = command(service, case, 10, ChatRequest, message='Supplied scenario.', mode='numeric', numeric=occupancy(metric_id='invented'))
    database.commit()
    code, _ = request(app, 'POST', f'/cases/{case.id}/sections/10/chat', cmd.model_dump_json().encode())
    assert code == 422
    database.expire_all()
    assert not [m for m in service.repo.list_for_case(s.ChatMessage, case.id) if m.section_id == 10]
