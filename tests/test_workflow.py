"""B16 offline API matrix, real B25 gates, locking, history and finality."""
from concurrent.futures import ThreadPoolExecutor
import json

import pytest
from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from backend.app import schemas as s
from backend.app.database import create_database
from backend.app.main import create_app
from backend.app.repository import Repository
from backend.app.services.locks import require_working, WorkflowConflict
from backend.app.services.readiness import ReadinessService
from backend.app.services.templates import TemplateRegistry
from backend.app.services.versions import VersionService, VersionRequest
from backend.app.team_config import TeamConfig, load_team
from test_intake import make_case, request, ROOT


@pytest.fixture
def ready(tmp_path):
    """Small labelled storage fixture; real readiness, confirmation and B25 logic."""
    engine, sessions = create_database(tmp_path/'workflow.sqlite')
    storage, templates = tmp_path/'blobs', tmp_path/'templates'
    with sessions.begin() as session:
        repo = Repository(session)
        case = make_case(repo, borrower_name='SYNTHETIC DEMO DATA — workflow fixture')
        TemplateRegistry(repo, templates).seed_owner_templates('fig', ROOT)
        template = TemplateRegistry(repo, templates).active('fig')
        for state in ReadinessService(repo).refresh(case.id)[1]:
            draft = repo.save(s.DraftVersion(case_id=case.id, section_id=state.section_id,
                text='SYNTHETIC DEMO DATA — workflow fixture, no financial claims.',
                config_hash=case.config_hash, prompt_version='test', model_version='mock',
                template_version_id=template.id, input_fingerprint=state.input_fingerprint, author='ca'))
            repo.save(state.model_copy(update=dict(current_draft_id=draft.id, readiness='Drafted')))
            VersionService(repo, storage, templates).confirm(case.id, state.section_id, VersionRequest(
                actor='ca', expected_draft_id=draft.id, expected_revision=state.editor_revision,
                expected_input_fingerprint=state.input_fingerprint))
    app = create_app(sessions=sessions, storage_root=storage, template_storage_root=templates)
    fixture = API(app, case.id, sessions)
    try:
        yield fixture
    finally:
        engine.dispose()


class API:
    def __init__(self, app, case_id, sessions):
        self.app, self.case_id, self.sessions = app, case_id, sessions
        self.prefix = f'/cases/{case_id}'

    def get(self, path):
        code, body = request(self.app, 'GET', self.prefix+path)
        assert code == 200, body
        return body

    def post(self, path, body, expected=200):
        code, result = request(self.app, 'POST', self.prefix+path, json.dumps(body).encode())
        assert code == expected, result
        return result

    def command(self, action, role, **kw):
        view = self.get('/workflow')
        return dict(actor='synthetic-human', role=role, action=action, expected_state=view['state'],
            expected_event_id=view['latest_event_id'], expected_es_version_id=view['active_es_version_id']) | kw

    def gate(self):
        report = self.get('/submission-checks/preview')
        return dict(expected_preview_token=report['preview_token'],
                    mandatory_gap_reasons={g['id']: 'SYNTHETIC DEMO DATA — owner follow-up pending.'
                                           for g in report['mandatory_gaps']})

    def move(self, action, role, expected=200, **kw):
        return self.post('/workflow/transitions', self.command(action, role, **kw), expected)

    def submitted(self):
        return self.move('submit', 'CA', **self.gate())

    def approver(self):
        self.submitted()
        supported = self.move('support', 'Credit Head')
        assert supported['state'] == 'Supported' and supported['locked']
        return self.move('handoff', 'Credit Head')

    def snapshot(self, es_id):
        return self.get('/workflow/snapshots/'+es_id)


def test_submit_gate_current_tokens_roles_and_atomic_retries(ready):
    a = ready
    before = a.get('/workflow')
    a.move('submit', 'CA', 422)
    a.move('submit', 'Credit Head', 403, **a.gate())
    a.move('submit', 'CA', 409, expected_preview_token='old')
    a.move('submit', 'CA', 409, expected_preview_token=a.gate()['expected_preview_token'])
    a.move('submit', 'CA', 422, **(a.gate() | {'mandatory_gap_reasons': {'other-case': 'Reason'}}))
    assert a.get('/workflow') == before
    assert not a.get('/submission-checks')
    command = a.command('submit', 'CA', **a.gate())
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: request(a.app, 'POST', a.prefix+'/workflow/transitions',
                                                  json.dumps(command).encode()), range(2)))
    assert sorted(code for code, _ in results) == [200, 409]
    state = a.get('/workflow')
    assert len(state['events']) == 1 and state['state'] == 'Submitted to Credit Head'
    saved = a.snapshot(state['active_es_version_id'])
    assert saved['submission_check']['passed'] and len(saved['sections']) == 14
    assert saved['es']['gap_reasons'] and saved['es']['purpose'] == 'submission'
    assert saved['submission_check']['report']['future_credit_master']['status'] == 'not connected'


def test_return_named_sections_reconfirm_dependencies_and_resubmit(ready):
    a = ready
    submitted = a.submitted()
    original = a.snapshot(submitted['active_es_version_id'])
    for fields in ({}, {'section_ids': [9]}, {'comment': 'Fix it'},
                   {'section_ids': [99], 'comment': 'Fix it'}, {'section_ids': [9, 9], 'comment': 'Fix it'}):
        a.move('return', 'Credit Head', 422, **fields)
    returned = a.move('return', 'Credit Head', section_ids=[9], comment='Clarify repayment sources.')
    assert returned['state'] == 'Returned to CA' and not returned['locked']
    assert returned['editable_sections'] == [9, 11, 14]
    assert returned['events'][-1]['returned_sections'] == [9]
    report = a.get('/submission-checks/preview')
    assert {v['section_id'] for v in report['sections'] if v['status'] == 'open'} == {9, 11, 14}
    a.move('submit', 'CA', 409, **a.gate())
    for sid in (1, 9, 11, 14):
        state = a.get(f'/sections/{sid}/history')['section']
        command = dict(actor='ca', expected_draft_id=state['current_draft_id'],
            expected_revision=state['editor_revision'], expected_input_fingerprint=state['input_fingerprint'])
        a.post(f'/sections/{sid}/confirm', command, 409 if sid == 1 else 200)
    resubmitted = a.submitted()
    assert resubmitted['state'] == 'Submitted to Credit Head'
    assert a.snapshot(resubmitted['active_es_version_id'])['es']['parent_id'] == original['es']['id']
    assert a.snapshot(original['es']['id'])['sections'] == original['sections']
    # An old support command cannot apply after a return/resubmit ABA cycle.
    stale = dict(actor='head', role='Credit Head', action='support', expected_state=submitted['state'],
                 expected_event_id=submitted['latest_event_id'], expected_es_version_id=submitted['active_es_version_id'])
    a.post('/workflow/transitions', stale, 409)
    with a.sessions() as session:
        comments = Repository(session).list_for_case(s.Comment, a.case_id)
        assert len(comments) == 1 and comments[0].section_id == 9
        assert comments[0].es_version_id == original['es']['id']


@pytest.mark.parametrize('outcome,purpose,fields', [
    ('approve', 'approved', {}), ('decline', 'declined', {}),
    ('approve_with_conditions', 'approved with conditions', {'conditions': ['SYNTHETIC DEMO DATA — obtain the signed certificate.']}),
])
def test_final_outcomes_immutable_snapshots_and_restart(ready, outcome, purpose, fields):
    a = ready
    review = a.approver()
    previous = a.snapshot(review['active_es_version_id'])
    result = a.move(outcome, 'Credit Approver', **fields)
    assert result['final'] and result['locked'] and not result['available_actions']
    snapshot = a.snapshot(result['active_es_version_id'])
    assert snapshot['es']['purpose'] == purpose and snapshot['es']['parent_id'] == previous['es']['id']
    assert snapshot['sections'] == previous['sections'] and snapshot['submission_check'] == previous['submission_check']
    assert result['events'][-1]['actor'] == 'synthetic-human'
    assert result['events'][-1]['payload']['conditions'] == fields.get('conditions', [])
    for action in ('submit', 'support', 'handoff', 'return', 'question', 'answer_resubmit', 'approve', 'approve_with_conditions', 'decline'):
        a.move(action, 'CA', 409)
    with a.sessions() as session:
        repo = Repository(session)
        es = repo.get(s.ESVersion, snapshot['es']['id'])
        with pytest.raises(ValueError, match='append-only'):
            repo.save(es.model_copy(update={'author': 'changed'}))
        for table, record_id in [('e_s_version', es.id), ('draft_version', next(iter(es.section_versions.values()))),
                                 ('workflow_event', result['latest_event_id'])]:
            for operation in ('UPDATE', 'DELETE'):
                with pytest.raises(IntegrityError, match='immutable'):
                    session.execute(text(f'UPDATE {table} SET id=id WHERE id=:id' if operation == 'UPDATE'
                                         else f'DELETE FROM {table} WHERE id=:id'), {'id': record_id})
                session.rollback()
        other = make_case(repo)
        session.commit()
        code, _ = request(a.app, 'GET', f'/cases/{other.id}/workflow/snapshots/{es.id}')
        assert code == 422
    assert a.snapshot(es.id) == snapshot
    # New factory/session against the same database retains the final state and history.
    restarted = create_app(sessions=a.sessions, storage_root='unused', template_storage_root='unused')
    assert API(restarted, a.case_id, a.sessions).get('/workflow') == result


def test_question_answer_only_repeated_cycles_and_resubmission(ready):
    a = ready
    review = a.approver()
    for cycle in range(2):
        a.move('question', 'Credit Approver', 422)
        asked = a.move('question', 'Credit Approver', section_ids=[9], question=f'Clarify existing wording, cycle {cycle}.')
        question = asked['questions'][-1]
        assert asked['locked'] and asked['editable_sections'] == []
        a.move('answer_resubmit', 'CA', 422, question_id=question['id'], **a.gate())
        a.move('answer_resubmit', 'CA', 409, question_id='other-question', answer='Clarification.', **a.gate())
        for role in ('Credit Head', 'Credit Approver', 'template admin'):
            a.move('answer_resubmit', role, 403, question_id=question['id'], answer='Clarification.', **a.gate())
        altered = a.gate()
        altered['mandatory_gap_reasons'][next(iter(altered['mandatory_gap_reasons']))] = 'Changed reason'
        a.move('answer_resubmit', 'CA', 409, question_id=question['id'], answer='Clarification.', **altered)
        answered = a.move('answer_resubmit', 'CA', question_id=question['id'], answer='SYNTHETIC DEMO DATA — existing wording clarified.', **a.gate())
        assert answered['state'] == 'With Credit Approver'
        saved = answered['questions'][-1]
        assert saved['answered_by'] and saved['answered_at'] and saved['resubmitted_es_version_id'] == answered['active_es_version_id']
        assert a.snapshot(answered['active_es_version_id'])['sections'] == a.snapshot(review['active_es_version_id'])['sections']
        with a.sessions() as session:
            repo = Repository(session)
            q = repo.get(s.ApproverQuestion, question['id'])
            with pytest.raises(ValueError, match='immutable'):
                repo.save(q.model_copy(update={'answer': 'Replacement'}))
            for sql in ('UPDATE approver_question SET question=question WHERE id=:id',
                        'DELETE FROM approver_question WHERE id=:id'):
                with pytest.raises(IntegrityError, match='immutable'):
                    session.execute(text(sql), {'id': q.id})
                session.rollback()
    final = a.move('approve', 'Credit Approver')
    assert len(final['questions']) == 2 and all(q['answer'] for q in final['questions'])
    assert [e['action'] for e in final['events']] == ['submit', 'support', 'handoff', 'question',
        'answer_resubmit', 'question', 'answer_resubmit', 'approve']


def test_approver_return_goes_through_credit_head_again(ready):
    a = ready
    a.approver()
    a.move('return', 'Credit Approver', section_ids=[9], comment='Revise section 9.')
    a.move('approve', 'Credit Approver', 409)
    for sid in (9, 11, 14):
        st = a.get(f'/sections/{sid}/history')['section']
        a.post(f'/sections/{sid}/confirm', dict(actor='ca', expected_draft_id=st['current_draft_id'],
               expected_revision=st['editor_revision'], expected_input_fingerprint=st['input_fingerprint']))
    a.submitted()
    a.move('handoff', 'Credit Head', 409)
    a.move('support', 'Credit Head')
    a.move('handoff', 'Credit Head')
    a.move('decline', 'Credit Approver')


def test_all_disallowed_state_role_action_combinations(ready):
    """Exercise the complete configured matrix without mocking the transition selector."""
    a = ready
    original = a.submitted()
    config = load_team('fig').workflow
    roles = config.roles + ['credit admin support']
    actions = sorted({t.action for t in config.transitions})
    count = 0
    for state in config.states:
        with a.sessions.begin() as session:
            repo = Repository(session)
            repo.save(repo.get(s.Case, a.case_id).model_copy(update={'workflow_state': state}))
        view = a.get('/workflow')
        for action in actions:
            candidates = [t for t in config.transitions if t.enabled and state in t.from_states and t.action == action]
            for role in roles:
                if any(t.role == role for t in candidates):
                    continue  # Success paths, required payloads and B25 covered separately.
                a.move(action, role, 403 if candidates and not view['final'] else 409)
                count += 1
        assert a.get('/workflow')['events'] == original['events']
    assert count > 380


@pytest.mark.parametrize('state', ['Submitted to Credit Head', 'Supported', 'With Credit Approver',
                                   'Question to CA', 'Approved', 'Approved with conditions', 'Declined'])
def test_mutation_api_lock_bypasses_and_repository_guards(ready, state):
    a = ready
    with a.sessions.begin() as session:
        repo = Repository(session)
        repo.save(repo.get(s.Case, a.case_id).model_copy(update={'workflow_state': state}))
    section = a.get('/sections/9/history')['section']
    base = dict(actor='ca', expected_draft_id=section['current_draft_id'], expected_revision=section['editor_revision'],
                expected_input_fingerprint=section['input_fingerprint'])
    operations = [
        ('/drafts/sections/9', {'actor': 'ca'}), ('/sections/9/confirm', base),
        ('/sections/9/redraft', base), ('/sections/9/save', base | {'replacements': {'claim': 'Edit'}}),
        ('/sections/9/chat', base | {'message': 'SYNTHETIC DEMO DATA clarification.'}),
        ('/public-search', {'actor': 'ca'}),
        ('/model', {'actor': 'ca', 'model_id': 'mock-v1', 'expected_model_id': 'mock-v1'}),
        ('/spreads', dict(profile='reit', evidence_ids=['x'], periods=['2025'], scope='group')),
        ('/analytics', dict(period='2025', scope='group', reviewed_by='ca', review_note='Review')),
    ]
    for path, body in operations:
        a.post(path, body, 409)
    if state not in {'Approved', 'Approved with conditions', 'Declined'}:
        a.post('/documents/scan', {'folder_id': 'unknown'}, 409)
        code, _ = request(a.app, 'POST', a.prefix+'/documents', b'SYNTHETIC DEMO DATA\nnew evidence',
                          query={'filename': 'new.txt'})
        assert code == 409
    with a.sessions() as session:
        repo = Repository(session)
        for sid in (None, 9):
            with pytest.raises(WorkflowConflict):
                require_working(repo, a.case_id, sid)
        st = repo.get(s.Section, section['id'])
        with pytest.raises(WorkflowConflict):
            repo.save(st.model_copy(update={'confirmed_draft_id': None, 'readiness': 'Drafted'}))
        with pytest.raises(WorkflowConflict):
            repo.save(s.Spread(case_id=a.case_id, document_ids=[], version='test', values={}, validation_status='valid'))
        case = repo.get(s.Case, a.case_id)
        with pytest.raises(WorkflowConflict):
            repo.save(case.model_copy(update={'ca_position': 'Changed position'}))


def test_configured_conditions_toggle_and_reserved_admin_handoff(ready):
    a = ready
    # Pin a valid alternate configuration through a separate case, as live cases never upgrade their pin.
    data = load_team('fig').model_dump(mode='json', exclude_unset=True)
    data['workflow']['transitions'][6]['enabled'] = False
    config = TeamConfig.model_validate(data)
    with a.sessions.begin() as session:
        repo = Repository(session, config_loader=lambda _: config)
        case = repo.save(s.Case(borrower_name='SYNTHETIC DEMO DATA alternate', team_id='fig',
            config_version=config.template.version, config_hash=config.content_hash,
            config_snapshot=config.model_dump(mode='json', exclude_unset=True),
            case_type='new', borrower_type='reit', existing_client=False, new_to_bank=True,
            workflow_state='With Credit Approver'))
    alternate = API(a.app, case.id, a.sessions)
    assert 'approve_with_conditions' not in [t['action'] for t in alternate.get('/workflow')['available_actions']]
    alternate.move('approve_with_conditions', 'Credit Approver', 409, conditions=['Condition'])
    data['workflow']['credit_admin_support_enabled'] = True
    data['workflow']['roles'].append('credit admin support')
    next(t for t in data['workflow']['transitions'] if t['action'] == 'handoff')['role'] = 'credit admin support'
    extension = TeamConfig.model_validate(data)
    assert next(t.role for t in extension.workflow.transitions if t.action == 'handoff') == 'credit admin support'
    assert not load_team('fig').workflow.credit_admin_support_enabled
    for change in ('final_states', 'locked_states'):
        broken = load_team('fig').model_dump(mode='json')
        broken['workflow'][change].remove('Declined')
        with pytest.raises(ValidationError):
            TeamConfig.model_validate(broken)


def test_submission_rechecks_confirmations_and_rejects_client_supplied_pass(ready):
    a = ready
    old_gate = a.gate()
    a.post('/submission-checks/validate', dict(actor='ca', **old_gate))
    with a.sessions.begin() as session:
        repo = Repository(session)
        state = next(v for v in repo.list_for_case(s.Section, a.case_id) if v.section_id == 9)
        repo.save(state.model_copy(update=dict(confirmed_draft_id=None, readiness='Drafted', editor_revision=state.editor_revision+1)))
    before = a.get('/workflow')
    a.move('submit', 'CA', 409, **old_gate)
    a.move('submit', 'CA', 409, **a.gate())
    a.post('/workflow/transitions', a.command('submit', 'CA', **a.gate()) | {'passed': True}, 422)
    assert a.get('/workflow') == before
    assert len(a.get('/submission-checks')) == 1


def test_required_conditions_payload_and_actor_validation(ready):
    a = ready
    a.approver()
    for conditions in ([], [''], [' \n ']):
        a.move('approve_with_conditions', 'Credit Approver', 422, conditions=conditions)
    a.move('approve', 'Credit Approver', 422, conditions=['Unrecorded outcome conditions'])
    a.move('support', 'Credit Head', 409)
    for field, value in [('actor', '  '), ('role', 'unknown')]:
        a.post('/workflow/transitions', a.command('approve', 'Credit Approver') | {field: value}, 422)
    assert a.get('/workflow')['state'] == 'With Credit Approver'
    assert request(a.app, 'GET', '/cases/unknown/workflow')[0] == 404


@pytest.mark.slow
def test_real_demo_return_question_approve_and_late_evidence(tmp_path):
    """Actual synthetic tranches, saved public pack and sourced mock drafts end to end."""
    from backend.app.local import create_demo_app, seed_case
    from test_dashboard import get_snapshot, ingest_tranche
    app = create_demo_app(tmp_path)
    engine, sessions = create_database(tmp_path/'wb_credit.sqlite')
    case = seed_case(sessions)
    a = API(app, case.id, sessions)
    actor = dict(actor='demo-ca', role='CA')
    try:
        data = get_snapshot(app, case)
        for tranche in (1, 2, 3):
            ingest_tranche(app, case, data, tranche, 'scan')
        a.post('/public-search', actor)
        for doc in a.get('/dashboard')['documents']:
            if doc['origin'] == 'public':
                a.post(f"/documents/{doc['id']}/confirm", actor)
        a.post('/demo/spread', actor)
        a.move('submit', 'CA', 409, **a.gate())
        for sid in (1, 2, 3, 4, 5, 6, 7, 8, 10, 9, 11, 12, 13, 14):
            extra = {'ca_position': 'Defer pending the requested review.'} if sid == 14 else {'confirm_unsecured': True}
            a.post(f'/drafts/sections/{sid}', actor | extra)

        def section_command(sid):
            st = a.get(f'/sections/{sid}/history')['section']
            return actor | dict(expected_draft_id=st['current_draft_id'], expected_revision=st['editor_revision'],
                                expected_input_fingerprint=st['input_fingerprint'])

        # A pending chat proposal must also be unusable after submit.
        proposal = a.post('/sections/9/chat', section_command(9) | dict(message='SYNTHETIC DEMO DATA — clarification pending.'))
        for sid in range(1, 15):
            a.post(f'/sections/{sid}/confirm', section_command(sid))
        first = a.submitted()
        a.post(f"/sections/9/chat/{proposal['id']}/decision", actor | {'action': 'reject'}, 409)
        a.post(f"/sections/9/chat/{proposal['id']}/decision", actor | {'action': 'accept'}, 409)
        assert a.get('/sections/9/chat')['proposals'][0]['status'] == 'stale'
        a.post('/demo/spread', actor, 409)
        a.post(f"/documents/{doc['id']}/confirm", actor, 409)
        a.post('/sections/9/compare', section_command(9) | {'model_ids': ['mock-v1', 'mock-v2']}, 409)
        gap_id = a.get('/submission-checks/preview')['mandatory_gaps'][0]['id']
        a.post(f'/expected-documents/{gap_id}/dismiss', actor | {'reason': 'Dismiss'}, 409)
        a.post(f'/expected-documents/{gap_id}/restore', actor | {'reason': 'Restore'}, 409)
        original = a.snapshot(first['active_es_version_id'])
        a.move('return', 'Credit Head', section_ids=[9], comment='Clarify repayment sources and refresh dependants.')
        for sid in (9, 11, 14):
            a.post(f'/sections/{sid}/redraft', section_command(sid))
            a.post(f'/sections/{sid}/confirm', section_command(sid))
        again = a.submitted()
        assert again['active_es_version_id'] != first['active_es_version_id']
        assert a.snapshot(first['active_es_version_id'])['sections'] == original['sections']
        a.move('support', 'Credit Head')
        a.move('handoff', 'Credit Head')
        asked = a.move('question', 'Credit Approver', section_ids=[9], question='Clarify the stated repayment basis.')
        a.move('answer_resubmit', 'CA', question_id=asked['questions'][-1]['id'],
               answer='The repayment basis is as stated in section 9; no figures or position changed.', **a.gate())
        final = a.move('approve_with_conditions', 'Credit Approver', conditions=['SYNTHETIC DEMO DATA — obtain the signed certificate.'])
        snapshot = a.snapshot(final['active_es_version_id'])
        assert len(snapshot['sections']) == 14 and snapshot['submission_check']['passed']
        assert snapshot['sections']['9']['claim_spans'][0]['source_register']
        (tmp_path/'workflow-final.json').write_text(json.dumps(final, indent=2))
        (tmp_path/'workflow-snapshot.json').write_text(json.dumps(snapshot, indent=2))
        preset = next(p for p in data['intake']['presets'] if p['tranche'] not in (1, 2, 3))
        source = next((ROOT/'demo/synthetic').rglob(preset['filename']))
        code, body = request(app, 'POST', a.prefix+'/documents', source.read_bytes(),
            query={'filename': source.name, 'metadata': json.dumps(preset['metadata'])})
        assert code == 200, body
        current = a.get('/submission-checks/preview')
        assert {v['section_id'] for v in current['sections'] if v['status'] == 'open'} == {8, 9, 11, 14}
        assert a.get('/workflow') == final
        assert a.snapshot(final['active_es_version_id']) == snapshot
        a.post('/sections/8/redraft', section_command(8), 409)
        restarted = API(create_demo_app(tmp_path), case.id, sessions)
        assert restarted.get('/workflow') == final
        assert restarted.snapshot(final['active_es_version_id']) == snapshot
    finally:
        engine.dispose()


def test_new_inputs_during_return_allow_explicit_stale_repairs(ready):
    from test_intake import source
    a = ready
    first = a.submitted()
    a.move('return', 'Credit Head', section_ids=[9], comment='Clarify repayment sources.')
    content = source(entity='SYNTHETIC DEMO DATA — workflow fixture').replace(b'Valuation report', b'Term sheet')
    code, body = request(a.app, 'POST', a.prefix+'/documents', content,
        query={'filename': 'term_sheet.txt', 'metadata': json.dumps({'catalogue_id': 2})})
    assert code == 200, body
    assert {8, 9, 11, 14} <= set(a.get('/workflow')['editable_sections'])
    with a.sessions.begin() as session:
        repo = Repository(session)
        require_working(repo, a.case_id, 8)
        state = next(st for st in repo.list_for_case(s.Section, a.case_id) if st.section_id == 8)
        old = repo.get(s.DraftVersion, state.current_draft_id)
        # A labelled fixture revision isolates the authorization after redraft:
        # the original stale marker is gone, but confirmation must remain possible.
        from uuid import uuid4
        revised = repo.save(old.model_copy(update=dict(id=str(uuid4()), parent_id=old.id,
            input_fingerprint=state.input_fingerprint, created_at=s.utcnow())))
        repo.save(state.model_copy(update=dict(current_draft_id=revised.id, confirmed_draft_id=None,
            readiness='Drafted', editor_revision=state.editor_revision+1)))
    st = a.get('/sections/8/history')['section']
    assert st['readiness'] == 'Drafted'
    assert 8 in a.get('/workflow')['editable_sections']
    a.post('/sections/8/confirm', dict(actor='ca', expected_draft_id=st['current_draft_id'],
        expected_revision=st['editor_revision'], expected_input_fingerprint=st['input_fingerprint']))
    a.move('submit', 'CA', 409, **a.gate())
    assert a.snapshot(first['active_es_version_id'])['es']['purpose'] == 'submission'


def test_checker_marks_sections_returns_queries_and_keeps_marks_on_unchanged_sections(ready):
    """Maker submits; checker marks sections reviewed or queries them; a returned section needs a fresh look on resubmission."""
    a = ready
    a.post('/review/marks', dict(actor='head', role='Credit Head', section_id=1, status='reviewed', expected_es_version_id='none'), 409)  # nothing submitted yet
    submitted = a.submitted()
    es = submitted['active_es_version_id']
    mark = lambda section, status, expected=200, **kw: a.post('/review/marks', dict(actor='head', role='Credit Head', section_id=section, status=status, expected_es_version_id=es) | kw, expected)
    review = a.get('/review')
    assert review['summary'] == dict(to_review=14, reviewed=0, queries=0) and 'not a credit decision' in review['note']
    mark(9, 'query', 422)                                    # a query needs a note
    mark(1, 'reviewed', 409, expected_es_version_id='old')   # a stale page cannot mark
    mark(1, 'reviewed', 422, role='CA')                      # the maker cannot mark
    a.post('/review/marks', dict(actor='approver', role='Credit Approver', section_id=1, status='reviewed', expected_es_version_id=es), 409)  # not with the approver
    for section in range(1, 15):
        if section != 9:
            mark(section, 'reviewed')
    review = mark(9, 'query', note='Clarify the refinancing source for the bullet.')
    assert review['summary'] == dict(to_review=14, reviewed=13, queries=1)
    nine = next(sec for sec in review['sections'] if sec['section_id'] == 9)
    assert nine['mark']['status'] == 'query' and nine['mark']['reviewer'] == 'head' and nine['mark_current']
    assert mark(2, 'cleared')['summary']['reviewed'] == 12 and mark(2, 'reviewed')['summary']['reviewed'] == 13

    # The checker returns the queried section. The maker sees the query on it and which sections are open to edit.
    a.move('return', 'Credit Head', section_ids=[9], comment='One query on section 9.')
    review = a.get('/review')
    by_id = {sec['section_id']: sec for sec in review['sections']}
    assert review['state'] == 'Returned to CA' and by_id[9]['returned'] and by_id[9]['mark']['note'].startswith('Clarify')
    assert [sid for sid, sec in by_id.items() if sec['editable']] == [9, 11, 14] and not by_id[1]['returned']
    assert any(c['body'] == 'One query on section 9.' and c['section_id'] == 9 for c in review['comments'])
    mark(1, 'reviewed', 409)  # no marking while the paper is back with the maker

    # The maker fixes section 9 (a new version), reconfirms and resubmits with a reply.
    with a.sessions.begin() as session:
        repo = Repository(session)
        state = next(st for st in repo.list_for_case(s.Section, a.case_id) if st.section_id == 9)
        old = repo.get(s.DraftVersion, state.current_draft_id)
        new = repo.save(s.DraftVersion.model_validate(old.model_dump() | dict(id='fixed-9', parent_id=old.id, text=old.text + ' Refinancing source added.')))
        repo.save(state.model_copy(update=dict(current_draft_id=new.id, editor_revision=state.editor_revision + 1)))
    assert a.get('/review')['sections'][8]['changed_since_submission']
    for sid in (9, 11, 14):
        state = a.get(f'/sections/{sid}/history')['section']
        a.post(f'/sections/{sid}/confirm', dict(actor='ca', expected_draft_id=state['current_draft_id'],
            expected_revision=state['editor_revision'], expected_input_fingerprint=state['input_fingerprint']))
    a.move('submit', 'CA', comment='Refinancing source added in section 9.', **a.gate())
    review = a.get('/review')
    by_id = {sec['section_id']: sec for sec in review['sections']}
    # Unchanged sections keep their marks; the changed one needs a fresh look and still shows the earlier query.
    assert review['summary'] == dict(to_review=14, reviewed=13, queries=0)
    assert by_id[9]['changed_since_mark'] and not by_id[9]['mark_current'] and by_id[9]['mark']['status'] == 'query' and by_id[1]['mark_current']
    assert [e['action'] for e in review['events']] == ['submit', 'return', 'submit']
    es = review['active_es_version_id']
    assert mark(9, 'reviewed')['summary'] == dict(to_review=14, reviewed=14, queries=0)
    assert a.move('support', 'Credit Head')['state'] == 'Supported'
