"""New information update: revised papers arrive after drafting; sections get proposals the maker applies.

Offline. The model is a stub that answers from the documents it is shown; no network, no paid call."""
from types import SimpleNamespace

import pytest

from backend.app import schemas as s
from backend.app.es2 import updates
from backend.app.services.drafting import DraftRequest
from backend.app.services.locks import RevisionConflict
from backend.app.services.versions import VersionRequest, VersionService
from test_es2 import stub_service


@pytest.fixture()
def case(tmp_path):
    """A fresh new-to-bank case with the first set of deal papers ingested. The late update folder is left for the test."""
    import os
    from fastapi.testclient import TestClient
    from backend.app.local import create_demo_app
    os.environ['LLM_PROVIDER'] = 'mock'
    api = TestClient(create_demo_app(tmp_path, 'demo/synthetic_keppel'))
    board = api.get(f"/cases/{api.get('/cases').json()[0]['id']}/dashboard").json()
    folders = board['intake']['folders']
    assert [f['id'] for f in folders] == ['deal_folder', 'late_update']
    first = api.post(f"/cases/{board['case']['id']}/documents/scan", json=dict(folder_id='deal_folder', metadata_by_path=folders[0]['metadata_by_path'])).json()
    assert len(first) == 11
    return SimpleNamespace(api=api, case=board['case'], runtime=tmp_path, late=folders[1])


def reply(request):
    """Answers from whichever papers are current: the amount in the term sheet and CAS, and the value in the valuation report."""
    user = request['messages'][0]['content']
    label = lambda name: next((line.split(']')[0][1:] for line in user.splitlines() if line.startswith('[E') and name in line), None)
    terms, value, cas, support = label('term_sheet'), label('valuation_report'), label('cas'), label('rm_support')
    late = 'term_sheet_rev2' in user
    amount, worth = ('650,000,000', '2,750.0') if late else ('600,000,000', '2,880.0')
    covenant = dict(raw='45', scale='unit', q='loan to value not exceeding 45%', c=[terms])
    if '"section": "1. ' in user:
        return dict(parts=dict(
            request=dict(paragraphs=[dict(v=f'The borrower requests a new secured term loan facility of SGD {amount} for five years.', c=[cas])]),
            # The model words this differently on the second pass although nothing it rests on has changed.
            justification=dict(paragraphs=[dict(v='The relationship manager is supportive of the request.' if late else 'The relationship manager supports the request.', c=[support])])))
    if '"section": "8. ' in user:
        return dict(parts=dict(ltv=dict(rows={'At proposed limit': {
            'Secured facility (SGD m)': dict(raw=amount, scale='unit', q=f'{amount}. Purpose: to refinance existing bank borrowings', c=[terms]),
            'Security value (SGD m)': dict(raw=worth, scale='million', q=f'Market value: SGD {worth} million.', c=[value]),
            'LTV covenant (%)': covenant}})))
    if '"section": "10. ' in user and terms:
        return dict(parts=dict(covenants=dict(rows=[{'Covenant': dict(v='Loan to value', c=[terms]), 'Requirement': dict(v='Loan to value not exceeding 45%', c=[terms]),
                                                     'Threshold': covenant, 'Direction': dict(v='max', c=[terms])}])))
    return dict(parts={})


@pytest.mark.slow
def test_revised_papers_give_proposals_that_the_maker_applies(case, monkeypatch):
    case_id = case.case['id']
    service, session, engine = stub_service(case, reply, monkeypatch)
    versions = VersionService(service.repo, case.runtime / 'blobs', case.runtime / 'templates')
    versions.drafting.live_client = service.live_client
    sections = lambda: {sec['section_id']: sec for sec in case.api.get(f'/cases/{case_id}/dashboard').json()['sections']}

    def token(n, **more):
        sec = sections()[n]
        return dict(actor='ca', role='CA', expected_draft_id=sec['current_draft_id'], expected_revision=sec['editor_revision'], expected_input_fingerprint=sec['input_fingerprint'], **more)

    def step(operation, *args):
        session.expire_all()
        result = operation(versions, case_id, *args)
        session.commit()
        return result
    look = lambda: {e['section_id']: e for e in step(updates.overview)['sections']}
    parts = lambda draft: draft['claim_spans'][0]['parts']
    try:
        first = {n: service.generate(case_id, n, DraftRequest(actor='ca')) for n in (1, 8, 9, 10)}
        session.commit()
        # The analyst adds a paragraph to section 1. It must survive the update.
        added = case.api.post(f'/cases/{case_id}/sections/1/blocks', json=token(1, op='add', kind='text', after='request', text='Site visit held with the relationship manager.'))
        assert added.status_code == 200, added.text
        before = step(updates.overview)
        assert before['available'] and before['documents'] == [] and before['sections'] == []

        # The revised papers arrive. Each replaces its earlier version; the affected sections are found.
        late = case.api.post(f'/cases/{case_id}/documents/scan', json=dict(folder_id='late_update', metadata_by_path=case.late['metadata_by_path'])).json()
        assert len(late) == 4 and all(r['outcome'] == 'created' and r['document']['supersedes_id'] and r['document']['conflict_status'] == 'none' for r in late)
        view = step(updates.overview)
        assert {d['filename']: d['replaces']['filename'] for d in view['documents']} == {
            'cas_rev2.pdf': 'cas.pdf', 'term_sheet_rev2.pdf': 'term_sheet.pdf', 'valuation_report_nov2026.pdf': 'valuation_report.pdf',
            'financial_projections_rev2.xlsx': 'financial_projections.xlsx'}
        state = {e['section_id']: e for e in view['sections']}
        assert state[1]['status'] == state[8]['status'] == 'ready' and view['open'] == 4
        # Section 10 reads the loan to value line of section 8, so it waits for section 8.
        assert state[10]['status'] == 'waiting' and state[10]['waiting_on'] == [8] and 8 in state[9]['waiting_on']
        with pytest.raises(ValueError, match='Update section 8 first'):
            step(updates.propose, 10, VersionRequest(**token(10)))

        # A proposal changes nothing in the section. Figures are compared cell by cell, in Python.
        proposal = step(updates.propose, 8, VersionRequest(**token(8)))
        assert sections()[8]['current_draft_id'] == first[8]['id'] and sections()[8]['readiness'] == 'Stale'
        ltv = next(c for c in proposal['changes'] if c['key'] == 'ltv')
        assert ltv['kind'] == 'figures' and ltv['locked'] and 'candidate' not in proposal
        cells = {c['column']: (c['before'], c['after'], c['computed']) for c in ltv['cells']}
        assert cells == {'Secured facility (SGD m)': ('600.0', '650.0', False), 'Security value (SGD m)': ('2,880.0', '2,750.0', False),
                         'LTV (%)': ('20.8', '23.6', True), 'Headroom (pp)': ('24.2', '21.4', True)}
        assert look()[8]['status'] == 'proposed'
        with pytest.raises(ValueError, match='figure tables are updated together'):
            step(updates.apply, proposal['id'], updates.ApplyRequest(**token(8, keep=['ltv'])))
        session.rollback()

        # Applying saves a new version on the current documents and releases the section that was waiting.
        eight = step(updates.apply, proposal['id'], updates.ApplyRequest(**token(8)))
        row = parts(eight)['ltv']['rows'][0]
        assert [cell['text'] for cell in row[1:5]] == ['650.0', '2,750.0', '23.6', '45'] and eight['parent_id'] == first[8]['id']
        assert sections()[8]['readiness'] == 'Drafted' and eight['claim_spans'][0]['update']['figures'] == ['ltv']
        late_ids = {r['document']['id'] for r in late}
        assert set(eight['document_ids']) & late_ids and not set(eight['document_ids']) & {r['document']['supersedes_id'] for r in late}
        state = look()
        assert state[8]['status'] == 'updated' and state[10]['status'] == 'ready' and state[10]['waiting_on'] == []
        ten = step(updates.apply, step(updates.propose, 10, VersionRequest(**token(10)))['id'], updates.ApplyRequest(**token(10)))
        headroom = next(r for r in parts(ten)['headroom']['rows'] if r[0]['text'] == 'Loan to value')
        assert headroom[2]['text'].startswith('23.6%') and headroom[3]['text'] == '21.4 pp'

        # Wording: only the part that rests on a replaced document is proposed. The reworded but unaffected part is kept.
        proposal = step(updates.propose, 1, VersionRequest(**token(1)))
        assert [c['key'] for c in proposal['changes']] == ['request'] and proposal['kept'] == ['justification']
        request = proposal['changes'][0]
        assert request['kind'] == 'wording' and request['cites_replaced'] and 'Cites a replaced document.' in request['reasons']
        assert '600,000,000' in request['before']['paragraphs'][0] and '650,000,000' in request['after']['paragraphs'][0]
        # The maker keeps the old wording. It is saved, flagged, and the section cannot be confirmed on a replaced source.
        one = step(updates.apply, proposal['id'], updates.ApplyRequest(**token(1, keep=['request'])))
        assert '600,000,000' in one['text'] and 'supports the request' in one['text'] and 'Site visit held' in one['claim_spans'][0]['blocks'][0]['text']
        state = look()
        assert state[1]['status'] == 'attention' and state[1]['kept_on_replaced'] == ['Requests'] and sections()[1]['readiness'] == 'Drafted'
        with pytest.raises(RevisionConflict, match='Superseded source'):
            step(lambda v, c: v.confirm(c, 1, VersionRequest(**token(1))))
        session.rollback()
        # A new proposal can be asked for; accepting it brings the wording onto the revised CAS. The unaffected part is still the first wording.
        proposal = step(updates.propose, 1, VersionRequest(**token(1)))
        one = step(updates.apply, proposal['id'], updates.ApplyRequest(**token(1)))
        assert '650,000,000' in one['text'] and '600,000,000' not in one['text'] and 'supports the request' in one['text']
        assert 'Site visit held' in one['claim_spans'][0]['blocks'][0]['text']
        claim = next(c for c in one['claim_spans'][1:] if c['part'] == 'request')
        assert one['text'][claim['start']:claim['end']] == claim['text']
        assert look()[1]['status'] == 'updated'
        assert step(lambda v, c: v.confirm(c, 1, VersionRequest(**token(1)))).readiness == 'CA confirmed'

        # A dismissed proposal leaves the section marked. A proposal is void once the section changes.
        proposal = step(updates.propose, 9, VersionRequest(**token(9)))
        interest = [c for part in proposal['changes'] if part['key'] == 'debt_service' for c in part['cells'] if c['row'] == 'Interest expense']
        assert interest and all((c['before'], c['after']) == ('23,175', '24,950') for c in interest)
        assert {e['section_id']: e for e in step(updates.dismiss, proposal['id'], updates.DismissRequest(**token(9)))['sections']}[9]['status'] == 'ready'
        proposal = step(updates.propose, 9, VersionRequest(**token(9)))
        moved = case.api.post(f'/cases/{case_id}/sections/9/blocks', json=token(9, op='add', kind='text', after='primary', text='Note added after the proposal.'))
        assert moved.status_code == 200, moved.text
        with pytest.raises(RevisionConflict, match='ask for a new proposal'):
            step(updates.apply, proposal['id'], updates.ApplyRequest(**token(9)))
        session.rollback()
        assert look()[9]['status'] == 'ready' and look()[9]['proposal'] is None
        nine = step(updates.apply, step(updates.propose, 9, VersionRequest(**token(9)))['id'], updates.ApplyRequest(**token(9)))
        assert 'Note added after the proposal.' in nine['claim_spans'][0]['blocks'][0]['text']
        assert step(updates.overview)['open'] == 0
        kinds = [p.status for p in service.repo.list_for_case(s.UpdateProposal, case_id) if p.section_id == 9]
        assert sorted(kinds) == ['applied', 'dismissed', 'superseded']
    finally:
        session.close(); engine.dispose()


def test_update_endpoints_and_the_first_generation_path(case):
    """The page reads one endpoint. A case with nothing replaced has nothing to show; a proposal needs a current token."""
    case_id = case.case['id']
    view = case.api.get(f'/cases/{case_id}/sections/updates')
    assert view.status_code == 200 and view.json()['available'] and view.json()['sections'] == [] and view.json()['open'] == 0
    assert not view.json()['live']  # no live run flag in tests: the page says proposals are off
    stale = dict(actor='ca', role='CA', expected_draft_id='none', expected_revision=0, expected_input_fingerprint='none')
    assert case.api.post(f'/cases/{case_id}/sections/8/update-proposal', json=stale).status_code in (409, 422)
    assert case.api.post(f'/cases/{case_id}/sections/update-proposals/unknown/apply', json=stale).status_code == 422


def test_text_cells_of_figure_tables_keep_their_wording_unless_they_rest_on_a_replaced_document():
    part = dict(key='pl', type='table', fill='extract')
    cell = lambda text, ref, **more: dict(text=text, cites=[ref], **more)
    old = dict(columns=['Item', 'FY2025', 'Remarks'], rows=[
        [dict(text='Revenue'), cell('100', 'ar', value='100'), cell('As reported.', 'ar')],
        [dict(text='Loan'), cell('600', 'ts1', value='600'), cell('Per the term sheet.', 'ts1')],
        [dict(text='Value'), cell('2,880', 'ar', value='2880'), cell('Year end valuation.', 'ar')]])
    new = dict(columns=['Item', 'FY2025', 'Remarks'], rows=[
        [dict(text='Revenue'), cell('100', 'ar', value='100'), cell('Reported in the annual report.', 'ar')],
        [dict(text='Loan'), cell('650', 'ts2', value='650'), cell('Per the revised term sheet.', 'ts2')],
        [dict(text='Value'), dict(text='', status='gap', cites=[]), cell('Valuation at the year end.', 'ar')]])
    register = dict(ar=dict(document_id='annual'), ts1=dict(document_id='old-terms'))
    merged = updates.keep_unaffected_text(part, old, new, register, {'old-terms'})
    rows = {row[0]['text']: [c.get('text') for c in row[1:]] for row in merged['rows']}
    # Reworded remark on an unchanged source: kept. Figure and remark on the replaced term sheet: updated.
    # A figure the model failed to copy this time, from a source that has not changed: the checked figure is kept.
    assert rows == {'Revenue': ['100', 'As reported.'], 'Loan': ['650', 'Per the revised term sheet.'], 'Value': ['2,880', 'Year end valuation.']}
    assert new['rows'][0][2]['text'] == 'Reported in the annual report.'  # the candidate itself is not altered
    assert updates.keep_unaffected_text(dict(part, fill='python'), old, new, register, {'old-terms'}) is new  # calculated tables are taken whole
