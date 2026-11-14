"""B13 actual late valuation, immutable edits, optimistic concurrency and history."""
import json
from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from backend.app import schemas as s
from backend.app.main import create_app
from backend.app.services.versions import VersionService, VersionRequest, EditRequest, RedraftRequest, RevisionConflict
from backend.app.services.intake import IntakeService
from backend.app.team_config import TeamConfig
from test_drafting import setup, generate, ROOT
from test_synthesis import prerequisites
from test_intake import request


def versions(service):
    return VersionService(service.repo, service.evidence.storage_root, service.templates.root, service.provider)


def state(service, case, sid):
    return next(st for st in versions(service).sections(case.id) if st.section_id == sid)


def command(service, case, sid, cls=VersionRequest, **kw):
    st = state(service, case, sid)
    return cls(actor='editor-ca', expected_draft_id=st.current_draft_id,
               expected_revision=st.editor_revision, expected_input_fingerprint=st.input_fingerprint, **kw)


def edit(service, case, sid, draft):
    claim = next(c for c in draft['claim_spans'][1:] if c['kind'] == 'narrative'
                 and not c.get('computed_value_ids') and not c.get('internal_rating')
                 and not c.get('requires_unsecured_confirmation'))
    replacement = claim['text'] + ' Further legal review is requested by the CA.'
    return versions(service).save(case.id, sid, command(service, case, sid, EditRequest,
                                            replacements={claim['id']: replacement}))


def revised_valuation(service, case):
    # Manifest locates the actual saved late report without rewriting source data.
    import yaml
    manifest = yaml.safe_load((ROOT/'demo/synthetic/manifest.yaml').read_text())
    item = next(f for f in manifest['documents'] if f['id']=='valuation-v2')
    path = ROOT/'demo/synthetic'/item['file']
    return IntakeService(service.repo, service.evidence.storage_root).ingest(case.id, path.name, path.read_bytes(),
        metadata=dict(entity=case.borrower_name, catalogue_id=9, period='2026-11-09', synthetic=True))


@pytest.mark.slow
def test_late_valuation_preserves_edited_confirmed_and_approved_snapshots(setup, database):
    service, case = setup
    upstream = prerequisites(service, case)
    upstream[14] = generate(service, case, 14, ca_position='Defer pending evidence.')
    edited = edit(service, case, 8, upstream[8])
    assert state(service, case, 11).readiness == 'Stale'
    # Refresh downstream explicitly in dependency order.
    for sid in (9, 11, 14):
        versions(service).redraft(case.id, sid, command(service, case, sid, RedraftRequest))
    for sid in (7, 8, 9, 11, 14):
        versions(service).confirm(case.id, sid, command(service, case, sid))
    before = {sid: state(service, case, sid) for sid in (7, 8, 9, 11, 14)}
    approved = service.repo.save(s.ESVersion(case_id=case.id, section_versions={sid:st.current_draft_id for sid,st in before.items()},
        config_hash=case.config_hash, template_version_id=edited['template_version_id'], author='approver', purpose='approved'))
    case.workflow_state='Approved'; case.active_es_version_id=approved.id; service.repo.save(case)
    revised = revised_valuation(service, case)
    assert revised.document.revision == 2
    after = {sid: state(service, case, sid) for sid in before}
    assert after[7].readiness == 'CA confirmed'
    assert all(after[sid].readiness == 'Stale' for sid in (8, 9, 11, 14))
    assert service.get(case.id, edited['id']) == edited
    assert service.repo.get(s.ESVersion, approved.id) == approved
    assert service.repo.get(s.Case, case.id).workflow_state == 'Approved'
    assert service.repo.get(s.Case, case.id).active_es_version_id == approved.id
    assert all(after[sid].current_draft_id == before[sid].current_draft_id for sid in before)
    assert len(service.repo.list_for_case(s.SectionConfirmation, case.id)) == 5
    database.commit(); database.expunge_all()
    assert state(service, case, 8).readiness == 'Stale'
    assert service.get(case.id, edited['id']) == edited


def test_redraft_parent_reset_template_and_downstream_versions(setup):
    service, case = setup
    upstream = prerequisites(service, case)
    versions(service).confirm(case.id, 7, command(service, case, 7))
    old = service.get(case.id, upstream[7]['id'])
    new = versions(service).redraft(case.id, 7, command(service, case, 7, RedraftRequest, confirm_unsecured=True))
    assert new['parent_id'] == old['id'] and new['id'] != old['id']
    assert new['template_version_id'] == old['template_version_id']
    assert state(service, case, 7).confirmed_draft_id is None
    assert state(service, case, 9).readiness == state(service, case, 11).readiness == 'Stale'
    assert service.get(case.id, old['id']) == old
    assert len(versions(service).history(case.id, 7)['confirmations']) == 1


def test_save_resets_confirmation_preserves_sources_and_synthesizes_ca_attribution(setup):
    service, case = setup
    upstream = prerequisites(service, case, 11)
    versions(service).confirm(case.id, 8, command(service, case, 8))
    new = edit(service, case, 8, upstream[8])
    assert new['parent_id'] == upstream[8]['id'] and new['ca_edits']
    assert new['document_ids'] == upstream[8]['document_ids']
    assert new['computed_value_ids'] == upstream[8]['computed_value_ids']
    assert new['gaps'] == upstream[8]['gaps']
    assert state(service, case, 8).confirmed_draft_id is None
    for sid in (9,):
        versions(service).redraft(case.id, sid, command(service, case, sid, RedraftRequest))
    eleven = generate(service, case, 11)
    assert 'Further legal review is requested by the CA.' in eleven['text']
    assert 'CA-edited wording: editor-ca;' in eleven['text']
    assert 'not independently verified' in eleven['text']
    for c in new['claim_spans'][1:]:
        assert c['text'] in new['text'][c['start']:c['end']]
    assert len([c for c in service.repo.list_for_case(s.Citation, case.id) if c.draft_id == new['id']]) > 0


@pytest.mark.parametrize('operation', ['save', 'redraft', 'confirm'])
@pytest.mark.parametrize('conflict', ['revision', 'draft', 'inputs'])
def test_stale_client_requests_rejected(setup, operation, conflict):
    service, case = setup
    draft = generate(service, case, 8)
    cls = {'save':EditRequest, 'redraft':RedraftRequest, 'confirm':VersionRequest}[operation]
    kwargs = {'replacements':{draft['claim_spans'][1]['id']:'unchanged'}} if operation=='save' else {}
    cmd = command(service, case, 8, cls, **kwargs)
    if conflict == 'revision': cmd.expected_revision += 1
    if conflict == 'draft': cmd.expected_draft_id = 'another-draft'
    if conflict == 'inputs': revised_valuation(service, case)
    with pytest.raises(RevisionConflict): getattr(versions(service), operation)(case.id, 8, cmd)
    assert service.get(case.id, draft['id']) == draft


def test_stale_save_keeps_stale_and_redraft_requires_fresh_confirmation(setup):
    service, case = setup
    draft = generate(service, case, 8)
    revised_valuation(service, case)
    edited = edit(service, case, 8, draft)
    assert state(service, case, 8).readiness == 'Stale'
    with pytest.raises(RevisionConflict, match='Stale'):
        versions(service).confirm(case.id, 8, command(service, case, 8))
    new = versions(service).redraft(case.id, 8, command(service, case, 8, RedraftRequest))
    assert new['parent_id'] == edited['id'] and state(service, case, 8).readiness == 'Drafted'
    assert 'SGD 104.00 million' in new['text']
    assert service.get(case.id, edited['id']) == edited
    assert versions(service).confirm(case.id, 8, command(service, case, 8)).readiness == 'CA confirmed'


@pytest.mark.parametrize('workflow', ['Submitted to Credit Head', 'Supported', 'With Credit Approver', 'Returned to CA', 'Question to CA', 'Approved', 'Approved with conditions', 'Declined'])
def test_review_and_final_locks(setup, workflow):
    service, case = setup
    draft = generate(service, case, 8)
    cmd = command(service, case, 8, RedraftRequest)
    case.workflow_state=workflow; service.repo.save(case)
    with pytest.raises(RevisionConflict, match='locked|named returned'):
        versions(service).redraft(case.id, 8, cmd)
    assert service.get(case.id, draft['id']) == draft


def test_protected_numeric_and_unknown_edits_cannot_change_computations(setup):
    service, case = setup
    draft = generate(service, case, 2)
    claim = next(c for c in draft['claim_spans'][1:] if c.get('computed_value_id'))
    for replacements in ({claim['id']:'invented values'}, {'unknown':'text'}):
        with pytest.raises(ValueError):
            versions(service).save(case.id, 2, command(service, case, 2, EditRequest, replacements=replacements))
    draft = generate(service, case, 8)
    claim = next(c for c in draft['claim_spans'][1:] if c['kind']=='narrative')
    for value in (' ', claim['text'] + ' SGD 999 million.', claim['text']):
        with pytest.raises(ValueError):
            versions(service).save(case.id, 8, command(service, case, 8, EditRequest, replacements={claim['id']:value}))
    assert service.get(case.id, draft['id']) == draft


def test_api_atomic_conflicts_role_history_and_restart(setup, database):
    service, case = setup
    generate(service, case, 8)
    cmd = command(service, case, 8, RedraftRequest)
    database.commit()
    sessions = sessionmaker(bind=database.bind)
    def app(): return create_app(sessions=sessions, storage_root=service.evidence.storage_root,
                                 template_storage_root=service.templates.root)
    prefix = f'/cases/{case.id}/sections/8'
    def call(): return request(app(), 'POST', prefix+'/redraft', cmd.model_dump_json().encode())
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _:call(), range(2)))
    assert sorted(code for code,_ in results) == [200,409]
    status, history = request(app(), 'GET', prefix+'/history')
    assert status == 200 and len(history['versions']) == 2
    invalid = cmd.model_dump() | {'role':'Credit Head'}
    assert request(app(), 'POST', prefix+'/confirm', json.dumps(invalid).encode())[0] == 422
    assert request(app(), 'POST', prefix+'/redraft', cmd.model_dump_json().encode())[0] == 409
    assert len(request(app(), 'GET', prefix+'/history')[1]['versions']) == 2
    # A failure after dependency preparation must roll back, including CA position.
    assert request(app(), 'GET', '/cases/foreign/sections/8/history')[0] == 422


def test_confirmation_sql_immutable_and_source_integrity(setup, database):
    service, case = setup
    draft = generate(service, case, 8)
    versions(service).confirm(case.id, 8, command(service, case, 8))
    confirmation = service.repo.list_for_case(s.SectionConfirmation, case.id)[0]
    with pytest.raises(ValueError, match='append-only'): service.repo.save(confirmation)
    database.commit()
    with pytest.raises(IntegrityError):
        database.execute(text('DELETE FROM section_confirmation WHERE id=:id'), {'id':confirmation.id})
    database.rollback()
    doc = service.repo.get(s.Document, draft['document_ids'][0])
    (service.evidence.storage_root/doc.storage_path).write_bytes(b'corrupt')
    with pytest.raises(ValueError): versions(service).confirm(case.id, 8, command(service, case, 8))
    assert len(service.repo.list_for_case(s.SectionConfirmation, case.id)) == 1


def test_freshness_config_graph_validation_and_old_pin_compatibility(setup):
    service, case = setup
    original = TeamConfig.model_validate(case.config_snapshot)
    old = original.model_dump(mode='json', exclude_unset=True)
    next(d for d in old['dependencies']['items'] if d['section_id']==9).pop('freshness_requires')
    loaded = TeamConfig.model_validate(old)
    assert loaded.model_dump(mode='json', exclude_unset=True) == old
    for refs in ([999], [9]):
        bad = original.model_dump(mode='json', exclude_unset=True)
        next(d for d in bad['dependencies']['items'] if d['section_id']==8)['freshness_requires'] = refs
        with pytest.raises(ValueError, match='dependency|Dependency'): TeamConfig.model_validate(bad)


def test_upstream_edit_invalidates_open_editor_and_stale_is_sticky(setup):
    service, case = setup
    prerequisites(service, case, 9)
    generate(service, case, 9)
    pending = command(service, case, 9, RedraftRequest)
    versions(service).redraft(case.id, 7, command(service, case, 7, RedraftRequest))
    with pytest.raises(RevisionConflict): versions(service).redraft(case.id, 9, pending)
    original = generate(service, case, 8)
    revised = revised_valuation(service, case).document
    assert state(service, case, 8).readiness == 'Stale'
    revised.conflict_status='rejected'; service.repo.save(revised)
    reverted = state(service, case, 8)
    assert reverted.input_fingerprint == original['input_fingerprint']
    assert reverted.readiness == 'Stale'
    assert state(service, case, 8) == reverted  # refresh is idempotent
    with pytest.raises(RevisionConflict): versions(service).confirm(case.id, 8, command(service, case, 8))
