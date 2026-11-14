"""B25 offline checks, real demo figures, immutable reasons and enforcing API."""
import json

import pytest
from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from backend.app import schemas as s
from backend.app.database import create_database
from backend.app.local import create_demo_app, seed_case
from backend.app.repository import Repository
from backend.app.services.submission_checks import (
    CheckRequest, MASTER_LABEL, SubmissionChecksService, SubmissionConflict, section_result,
)
from backend.app.services.templates import TemplateRegistry
from test_intake import make_case, request
from test_dashboard import ingest_tranche, get_snapshot
from test_drafting import setup, generate, ROOT


def checks(service):
    return SubmissionChecksService(service.repo, service.evidence.storage_root, service.templates.root)


def command(report, **kw):
    return CheckRequest(actor='checks-ca', expected_preview_token=report['preview_token'], **kw)


@pytest.mark.parametrize('sid', range(1, 15))
def test_each_section_requires_current_confirmation_or_reasoned_na(sid):
    state = s.Section(case_id='c', section_id=sid, input_fingerprint='now', current_draft_id='d',
        confirmed_draft_id='d', readiness='CA confirmed', editor_revision=2)
    draft = s.DraftVersion(case_id='c', section_id=sid, id='d', text='SYNTHETIC DEMO DATA',
        config_hash='hash', prompt_version='mock', model_version='mock', template_version_id='t',
        input_fingerprint='now', author='ca')
    confirmation = s.SectionConfirmation(case_id='c', section_id=sid, draft_id='d',
        input_fingerprint='now', editor_revision=1, actor='ca')
    evaluate = lambda st, dr=draft, cs=[confirmation], issues=[]: section_result(st, 'section', dr, cs, issues)
    assert evaluate(state)['status'] == 'passed'
    assert evaluate(state, cs=[])['status'] == 'open'
    assert evaluate(state, issues=['Unavailable source'])['status'] == 'open'
    assert evaluate(state, dr=draft.model_copy(update={'input_fingerprint': 'old'}))['status'] == 'open'
    assert evaluate(state.model_copy(update={'editor_revision': 4}))['status'] == 'open'
    for status in ('Waiting for input', 'Can draft (partial)', 'Can draft (full)', 'Drafted', 'Stale'):
        assert evaluate(state.model_copy(update={'readiness': status}))['status'] == 'open'
    assert evaluate(state.model_copy(update={'current_draft_id': None}), dr=None)['status'] == 'open'
    na = state.model_copy(update={'applicable': False, 'readiness': 'Not applicable', 'na_reason': 'New to bank.'})
    assert evaluate(na, dr=None, cs=[])['status'] == 'passed'
    for reason in (None, '', ' \n\t'):
        # Invalid legacy state must fail closed, even if normal schema validation was bypassed.
        assert evaluate(na.model_copy(update={'na_reason': reason}), dr=None)['status'] == 'open'
    assert evaluate(state.model_copy(update={'readiness': 'Not applicable', 'na_reason': 'Waive it'}))['status'] == 'open'


@pytest.mark.parametrize('reason', ['', ' ', '\n\t'])
def test_blank_gap_reasons_rejected(reason):
    with pytest.raises(ValidationError):
        CheckRequest(actor='ca', expected_preview_token='token', mandatory_gap_reasons={'gap': reason})


def test_empty_case_gap_rules_and_recorded_failed_checks(database, tmp_path):
    repo = Repository(database)
    case = make_case(repo)
    templates = tmp_path/'templates'
    TemplateRegistry(repo, templates).seed_owner_templates('fig', ROOT)
    service = SubmissionChecksService(repo, tmp_path/'blobs', templates)
    report = service.preview(case.id)
    assert len(report['sections']) == 14 and not report['passed']
    assert report['future_credit_master']['facilities'] == []
    assert report['future_credit_master']['gaps']
    # Both unfulfilled alternatives are explicit items; one provided member will close both.
    alternatives = [g for g in report['mandatory_gaps'] if g['alternative_group']]
    assert len(alternatives) == 2
    reason_map = {g['id']: 'Requested from the responsible owner; review pending.' for g in report['mandatory_gaps']}
    recorded = service.record(case.id, command(report, mandatory_gap_reasons=reason_map))
    assert not recorded.passed
    assert all(g['status_check'] == 'passed' for g in recorded.report['mandatory_gaps'])
    assert all(g['recorded_reason'] for g in recorded.report['mandatory_gaps'])
    assert not recorded.report['can_submit']
    assert repo.get(s.ESVersion, recorded.es_version_id).gap_reasons == reason_map
    assert len(recorded.section_results) == 14
    with pytest.raises(SubmissionConflict, match='remain open'):
        service.record(case.id, command(report, mandatory_gap_reasons=reason_map), require_passed=True)
    assert len(repo.list_for_case(s.SubmissionCheck, case.id)) == 1
    with pytest.raises(ValueError, match='append-only'):
        repo.save(recorded)
    database.commit()
    with pytest.raises(IntegrityError, match='immutable'):
        database.execute(text('UPDATE submission_check SET passed=1 WHERE id=:id'), {'id': recorded.id})
    database.rollback()
    assert service.get(case.id, recorded.id) == recorded
    other = make_case(repo, borrower_name='SYNTHETIC DEMO DATA Other borrower')
    with pytest.raises(ValueError, match='not found in this case'):
        service.get(other.id, recorded.id)
    for gap_id in ('unknown', next(g['id'] for g in service.preview(other.id)['mandatory_gaps'])):
        with pytest.raises(ValueError, match='current open mandatory'):
            service.record(case.id, command(service.preview(case.id), mandatory_gap_reasons={gap_id: 'Reason'}))


def test_dismissal_public_partial_and_alternatives_do_not_silently_waive(setup):
    drafting, case = setup
    service = checks(drafting)
    report = service.preview(case.id)
    ids = {g['catalogue_id']: g for g in report['mandatory_gaps']}
    assert 4 in ids and 6 in ids  # Public report awaits CA confirmation.
    assert 7 in ids and 19 in ids  # Generate offers remain gaps.
    from backend.app.services.gaps import GapService
    GapService(drafting.repo).dismiss(case.id, ids[19]['id'], actor='ca', reason='Dismissed from requests')
    dismissed = service.preview(case.id)
    item = next(g for g in dismissed['mandatory_gaps'] if g['catalogue_id'] == 19)
    assert item['dismiss_reason'] and item['status_check'] == 'open' and item['recorded_reason'] is None
    for doc in drafting.repo.list_for_case(s.Document, case.id):
        if doc.origin == 'public':
            drafting.repo.save(doc.model_copy(update={'confirmed_by': 'ca', 'confirmed_at': s.utcnow()}))
    confirmed = service.preview(case.id)
    assert not {4, 6} & {g['catalogue_id'] for g in confirmed['mandatory_gaps']}
    with pytest.raises(SubmissionConflict, match='changed'):
        service.record(case.id, command(report))
    with pytest.raises(ValueError, match='current open mandatory'):
        service.record(case.id, command(confirmed, mandatory_gap_reasons={ids[4]['id']: 'Old gap reason'}))


def test_future_panel_uses_saved_python_figures_and_withholds_corrupt_sources(setup):
    drafting, case = setup
    draft = generate(drafting, case, 2)
    service = checks(drafting)
    report = service.preview(case.id)
    panel = report['future_credit_master']
    assert panel['label'] == MASTER_LABEL and panel['status'] == 'not connected'
    assert panel['included_in_pass_count'] is False and 'passed' not in panel
    assert panel['draft_id'] == draft['id']
    assert [(r['figures']['existing']['value'], r['figures']['outstanding']['value'], r['figures']['proposed']['value'])
            for r in panel['facilities']] == [('45', '42', '60'), ('10', '4', '15')]
    for facility in panel['facilities']:
        for figure in facility['figures'].values():
            assert figure['synthetic'] and figure['unit'] == 'currency_million' and figure['currency'] == 'SGD'
            assert figure['sources'] and figure['operand_evidence_ids'] and figure['computed_value_id']
            assert all(v['page'] and v['document_id'] for v in figure['sources'].values())
            assert 'master_balance' not in figure
    assert report['summary']['total'] == 14 + len(report['mandatory_gaps'])
    first = panel['facilities'][0]['figures']['existing']
    doc = drafting.repo.get(s.Document, next(iter(first['sources'].values()))['document_id'])
    path = drafting.evidence.storage_root/doc.storage_path
    path.write_bytes(b'SYNTHETIC DEMO DATA corrupted fixture')
    damaged = service.preview(case.id)
    assert next(v for v in damaged['sections'] if v['section_id'] == 2)['status'] == 'open'
    assert damaged['future_credit_master']['gaps']
    assert all(not r['figures'] for r in damaged['future_credit_master']['facilities'])


@pytest.mark.slow
def test_real_demo_api_open_passed_stale_history_and_restart(tmp_path):
    app = create_demo_app(tmp_path)
    engine, sessions = create_database(tmp_path/'wb_credit.sqlite')
    case = seed_case(sessions)
    prefix = f'/cases/{case.id}'
    actor = {'actor': 'demo-ca', 'role': 'CA'}

    def get(path):
        code, body = request(app, 'GET', prefix + path)
        assert code == 200, body
        return body

    def post(path, body, expected=200):
        code, result = request(app, 'POST', prefix + path, json.dumps(body).encode())
        assert code == expected, result
        return result

    def check_request(report, reasons=None):
        return actor | {'expected_preview_token': report['preview_token'], 'mandatory_gap_reasons': reasons or {}}

    try:
        initial = get('/submission-checks/preview')
        assert initial['summary']['open'] >= 14
        failed = post('/submission-checks', check_request(initial))
        assert not failed['passed']
        rejected = post('/submission-checks/validate', check_request(initial), 409)
        assert rejected['detail']['report']['summary']['open'] >= 14
        assert len(get('/submission-checks')) == 1
        data = get_snapshot(app, case)
        for tranche in (1, 2, 3):
            ingest_tranche(app, case, data, tranche, 'scan')
        post('/public-search', actor)
        for doc in get('/dashboard')['documents']:
            if doc['origin'] == 'public':
                post(f"/documents/{doc['id']}/confirm", actor)
        post('/demo/spread', actor)
        before_drafts = get('/submission-checks/preview')
        assert {g['catalogue_id'] for g in before_drafts['mandatory_gaps']} == {19}
        for sid in (1, 2, 3, 4, 5, 6, 7, 8, 10, 9, 11, 12, 13, 14):
            extras = {'ca_position': 'Defer pending the requested review.'} if sid == 14 else {'confirm_unsecured': True}
            post(f'/drafts/sections/{sid}', actor | extras)
        drafted = get('/submission-checks/preview')
        assert drafted['summary'] == dict(total=15, passed=0, open=15)
        gap_id = drafted['mandatory_gaps'][0]['id']
        reasons = {gap_id: 'Industry mapping remains outstanding; requested from the internal team for review.'}
        # Gap reasons alone cannot waive even one section confirmation.
        post('/submission-checks/validate', check_request(drafted, reasons), 409)
        for sid in range(1, 15):
            state = get(f'/sections/{sid}/history')['section']
            post(f'/sections/{sid}/confirm', actor | dict(expected_draft_id=state['current_draft_id'],
                expected_revision=state['editor_revision'], expected_input_fingerprint=state['input_fingerprint']))
        confirmed = get('/submission-checks/preview')
        assert confirmed['summary'] == dict(total=15, passed=14, open=1)
        post('/submission-checks/validate', check_request(drafted, reasons), 409)
        post('/submission-checks/validate', check_request(confirmed), 409)
        passed = post('/submission-checks/validate', check_request(confirmed, reasons))
        assert passed['passed'] and passed['report']['summary'] == dict(total=15, passed=15, open=0)
        assert len(passed['section_results']) == 14
        assert passed['mandatory_gap_reasons'] == reasons
        assert passed['report']['future_credit_master']['label'] == MASTER_LABEL
        (tmp_path/'b25-passed.json').write_text(json.dumps(passed, indent=2))
        with sessions.begin() as session:
            repo = Repository(session)
            es = repo.get(s.ESVersion, passed['es_version_id'])
            assert len(es.section_versions) == 14 and es.gap_reasons == reasons and es.purpose == 'submission'
            assert repo.get(s.Case, case.id).workflow_state == 'Draft'
            assert repo.get(s.Case, case.id).active_es_version_id is None
            assert not repo.list_for_case(s.WorkflowEvent, case.id)
        # Strict role/actor/request contracts and unknown/cross-case reason keys.
        post('/submission-checks', check_request(confirmed, reasons) | {'role': 'Credit Head'}, 422)
        post('/submission-checks', check_request(confirmed, reasons) | {'actor': '   '}, 422)
        post('/submission-checks', check_request(confirmed, {gap_id: '  '}), 422)
        post('/submission-checks', check_request(confirmed, {'unknown': 'Reason'}), 422)
        post('/submission-checks', check_request(confirmed, reasons) | {'passed': True}, 422)
        assert request(app, 'GET', '/cases/unknown/submission-checks/preview')[0] == 404
        # A real late valuation invalidates exactly the existing dependency chain.
        preset = next(p for p in data['intake']['presets'] if p['tranche'] not in (1, 2, 3))
        source = next((ROOT/'demo/synthetic').rglob(preset['filename']))
        code, body = request(app, 'POST', prefix+'/documents', source.read_bytes(),
            query={'filename': source.name, 'metadata': json.dumps(preset['metadata'])})
        assert code == 200, body
        stale = get('/submission-checks/preview')
        assert {v['section_id'] for v in stale['sections'] if v['status'] == 'open'} == {8, 9, 11, 14}
        assert stale['summary'] == dict(total=15, passed=10, open=5)
        post('/submission-checks/validate', check_request(confirmed, reasons), 409)
        post('/submission-checks/validate', check_request(stale, reasons), 409)
        assert get('/submission-checks/'+passed['id']) == passed
        (tmp_path/'b25-stale.json').write_text(json.dumps(stale, indent=2))
        app = create_demo_app(tmp_path)
        assert get('/submission-checks/'+passed['id']) == passed
        assert len(get('/submission-checks')) == 2
        for workflow in ('Submitted to Credit Head', 'Returned to CA', 'Question to CA', 'Approved', 'Declined'):
            with sessions.begin() as session:
                repo = Repository(session)
                repo.save(repo.get(s.Case, case.id).model_copy(update={'workflow_state': workflow}))
            locked = get('/submission-checks/preview')
            assert not locked['can_submit']
            post('/submission-checks', check_request(locked, reasons), 409)
            post('/submission-checks/validate', check_request(locked, reasons), 409)
    finally:
        engine.dispose()


def test_configured_na_and_explicit_nil_exposure(database, tmp_path):
    from backend.app.services.drafting import DraftingService
    repo = Repository(database)
    case = make_case(repo, case_type='new', existing_client=False, new_to_bank=True)
    templates = tmp_path/'templates'
    TemplateRegistry(repo, templates).seed_owner_templates('fig', ROOT)
    drafting = DraftingService(repo, tmp_path/'blobs', templates)
    generate(drafting, case, 2)
    report = checks(drafting).preview(case.id)
    conduct = next(v for v in report['sections'] if v['section_id'] == 13)
    assert conduct['status'] == 'passed' and conduct['na_reason'] and not conduct['draft_id']
    panel = report['future_credit_master']
    assert panel['case_input'] == dict(case_id=case.id, new_to_bank=True)
    assert panel['facilities'] == [] and 'explicit new-to-bank' in panel['exposure_note']
    assert panel['label'] == MASTER_LABEL and panel['status'] == 'not connected'
    recorded = checks(drafting).record(case.id, command(report))
    assert recorded.section_results[13]['na_reason'] == conduct['na_reason']


def test_additive_migration_preserves_legacy_checks(tmp_path):
    import sqlite3
    path = tmp_path/'migration.sqlite'
    engine, sessions = create_database(path)
    with sessions.begin() as session:
        repo = Repository(session)
        case = make_case(repo)
        templates = tmp_path/'templates'
        TemplateRegistry(repo, templates).seed_owner_templates('fig', ROOT)
        service = SubmissionChecksService(repo, tmp_path/'blobs', templates)
        record = service.record(case.id, command(service.preview(case.id)))
    engine.dispose()
    # Reproduce the pre-B25 schema, retaining the existing B01 record fields.
    with sqlite3.connect(path) as connection:
        connection.execute('ALTER TABLE submission_check DROP COLUMN report')
    engine, sessions = create_database(path)
    try:
        with sessions() as session:
            repo = Repository(session)
            loaded = repo.get(s.SubmissionCheck, record.id)
            assert loaded.report == {}
            assert loaded.model_dump(exclude={'report'}) == record.model_dump(exclude={'report'})
            with pytest.raises(IntegrityError, match='immutable'):
                session.execute(text('DELETE FROM submission_check WHERE id=:id'), {'id': record.id})
            session.rollback()
    finally:
        engine.dispose()
