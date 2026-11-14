"""B14 UI contracts against persisted real-pack claims and source pages, offline."""
import json

from sqlalchemy.orm import sessionmaker

from backend.app.main import create_app
from test_drafting import setup, generate
from test_intake import request
from test_versions import revised_valuation


def test_editor_api_save_confirm_late_source_redraft(setup, database, tmp_path):
    service, case = setup
    draft = generate(service, case, 8)
    database.commit()
    app = create_app(sessions=sessionmaker(bind=database.bind), storage_root=service.evidence.storage_root,
                     template_storage_root=service.templates.root)
    path = f'/cases/{case.id}/sections/8'

    def get_history():
        status, result = request(app, 'GET', path + '/history')
        assert status == 200
        return result

    def token(history):
        state = history['section']
        return dict(actor='editor-review-ca', role='CA', expected_draft_id=state['current_draft_id'],
                    expected_revision=state['editor_revision'], expected_input_fingerprint=state['input_fingerprint'])

    def post(action, body):
        return request(app, 'POST', path + '/' + action, json.dumps(body).encode())

    initial = get_history()
    claim = next(c for c in draft['claim_spans'][1:] if c['kind'] == 'narrative')
    status, edited = post('save', token(initial) | {'replacements': {claim['id']: claim['text'] + ' CA requests further legal review.'}})
    assert status == 200 and edited['parent_id'] == draft['id']
    assert edited['gaps'] == draft['gaps']
    assert edited['claim_spans'][0]['source_register'] == draft['claim_spans'][0]['source_register']
    assert post('confirm', token(initial))[0] == 409  # No silent overwrite from an old editor.
    current = get_history()
    assert post('confirm', token(current))[0] == 200
    confirmed = get_history()
    assert confirmed['section']['readiness'] == 'CA confirmed'
    assert len(confirmed['confirmations']) == 1
    # Every displayed source button resolves independently of the historical draft.
    sources = edited['claim_spans'][0]['source_register']
    for ref, snapshot in sources.items():
        status, resolved = request(app, 'GET', f'/cases/{case.id}/evidence/{ref}')
        assert status == 200 and resolved['page'] == snapshot['page']
        assert resolved['filename'] == snapshot['filename']
        assert resolved['content_hash'] == snapshot['content_hash']
        assert resolved['locator']['format'] == 'pdf'
        assert resolved['preview_url'].endswith(f'#page={resolved["page"]}')
    database.expire_all()
    revised_valuation(service, case)
    database.commit()
    stale = get_history()
    assert stale['section']['readiness'] == 'Stale'
    assert stale['section']['confirmed_draft_id'] == edited['id']  # Historical only.
    assert post('confirm', token(stale))[0] == 409
    old_valuation = next(v for v in sources.values() if v['catalogue_id'] == 9)
    status, historical = request(app, 'GET', f'/cases/{case.id}/evidence/{old_valuation["evidence_id"]}')
    assert status == 200 and not historical['current'] and historical['revision'] == 1
    status, fresh = post('redraft', token(stale) | {'confirm_unsecured': False})
    assert status == 200 and fresh['parent_id'] == edited['id']
    assert '104' in fresh['text'] and 'CA requests further legal review.' not in fresh['text']
    refreshed = get_history()
    assert refreshed['section']['confirmed_draft_id'] is None
    assert post('confirm', token(refreshed))[0] == 200
    final = get_history()
    assert len(final['versions']) == 3 and len(final['confirmations']) == 2
    assert next(d for d in final['versions'] if d['id'] == edited['id']) == edited
    (tmp_path / 'editor-draft.json').write_text(json.dumps(edited))


def test_computed_editor_sources_resolve_normalized_worksheet_and_public_pdf(setup, database, tmp_path):
    service, case = setup
    drafts = [generate(service, case, section) for section in (2, 10, 12)]
    database.commit()
    app = create_app(sessions=sessionmaker(bind=database.bind), storage_root=service.evidence.storage_root,
                     template_storage_root=service.templates.root)
    sources = [source for draft in drafts for source in draft['claim_spans'][0]['source_register'].values()]
    formats = set()
    for source in sources:
        status, resolved = request(app, 'GET', f'/cases/{case.id}/evidence/{source["evidence_id"]}')
        assert status == 200 and resolved['excerpt']
        formats.add(resolved['locator']['format'])
        if resolved['origin'] == 'public':
            assert resolved['url'] and resolved['retrieved_at'] and resolved['confirmed_by'] is None
        if resolved['locator']['format'] != 'pdf':
            assert resolved['synthetic'] and not resolved['preview_url']
    assert 'pdf' in formats and 'xlsx' in formats
    (tmp_path / 'editor-computed.json').write_text(json.dumps(drafts))
