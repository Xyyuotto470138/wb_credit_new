"""Offline acceptance: persisted B04 intake → expected list → section readiness."""
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path

import pytest
import yaml

from backend.app import schemas as s
from backend.app.database import create_database
from backend.app.main import create_app
from backend.app.repository import Repository
from backend.app.services.gaps import GapService, request_list
from backend.app.services.intake import IntakeService
from backend.app.services.readiness import ReadinessService
from backend.app.team_config import TeamConfig, load_team
from test_intake import request

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 11, 10, tzinfo=timezone.utc)


def make_case(repo, **changes):
    config = load_team('fig')
    return repo.save(s.Case(**(dict(borrower_name='SYNTHETIC DEMO DATA — Example REIT',
        team_id='fig', config_version=config.template.version, config_hash=config.content_hash,
        case_type='renewal', borrower_type='reit', existing_client=True, new_to_bank=False,
        public_entity=True) | changes)))


def doc(repo, case, catalogue_id, **changes):
    return repo.save(s.Document(**(dict(case_id=case.id, catalogue_id=catalogue_id,
        entity=case.borrower_name, content_hash=sha256(str((catalogue_id, changes)).encode()).hexdigest(),
        storage_path='runtime/test-fixture.txt', original_filename='SYNTHETIC DEMO DATA.txt',
        period='2026-10-31', origin='upload', synthetic=True) | changes)))


def refresh(repo, case):
    snapshot, sections = ReadinessService(repo).refresh(case.id)
    return snapshot, {section.section_id: section for section in sections}


def expected(snapshot, catalogue_id):
    return next(e for e in snapshot.expected if e.catalogue_id == catalogue_id)


def public_doc(repo, case, catalogue_id=4, **changes):
    return doc(repo, case, catalogue_id, **(dict(origin='public', url='https://example.org/report',
               retrieved_at=NOW, synthetic=False) | changes))


def confirm(repo, document):
    return repo.save(document.model_copy(update={'confirmed_by': 'demo-ca', 'confirmed_at': NOW}))


def test_empty_new_renewal_and_conditional_matrix(database):
    repo = Repository(database)
    new = make_case(repo, case_type='new', existing_client=False, new_to_bank=True, public_entity=False)
    snap, sections = refresh(repo, new)
    assert len([e for e in snap.expected if e.catalogue_id]) == 22
    assert sections[13].readiness == 'Not applicable' and sections[13].na_reason
    assert all(sections[i].readiness == 'Waiting for input' for i in range(1, 13))
    assert expected(snap, 3).status == expected(snap, 17).status == 'Not applicable'
    assert expected(snap, 9).status == 'Not applicable'
    assert not [e for e in snap.expected if e.suggestion_id]
    case = make_case(repo, borrower_type='fund', financial_covenants=True, covenants=True,
                     property_or_asset_security=True, insured_security_or_assets=True,
                     new_money=True, property_income_repayment=True, bureau_covered=True)
    snap, _ = refresh(repo, case)
    assert {e.catalogue_id for e in snap.expected if e.mandatory} == set(range(1, 23)) - {11, 12, 18}
    assert set(snap.groups) == {'RM', 'client', 'internal team'}
    assert expected(snap, 18).status == 'Missing' and not expected(snap, 18).mandatory
    assert not next(e for e in snap.expected if e.catalogue_id == 11).mandatory
    assert 'prior_condition_evidence' not in {e.suggestion_id for e in snap.expected}
    doc(repo, case, 22)
    snap, _ = refresh(repo, case)
    trigger = next(e for e in snap.expected if e.suggestion_id == 'prior_condition_evidence')
    assert trigger.status == 'Suggested' and not trigger.mandatory


@pytest.mark.parametrize('member', [4, 6])
def test_alternatives_confirmation_generation_and_dismissal(database, member):
    repo = Repository(database)
    case = make_case(repo)
    report = public_doc(repo, case, member)
    snap, _ = refresh(repo, case)
    assert expected(snap, member).status == 'Found publicly'
    assert not GapService(repo).satisfied(snap, expected(snap, member))
    assert expected(snap, 7).status == 'Can generate'
    # A generation offer is not a generated, validated result.
    assert not snap.support[7].usable
    confirm(repo, report)
    snap, _ = refresh(repo, case)
    assert all(GapService(repo).satisfied(snap, expected(snap, i)) for i in (4, 6))
    assert not {4, 6} & {e['catalogue_id'] for items in snap.groups.values() for e in items}
    cas = expected(snap, 1)
    service = GapService(repo)
    with pytest.raises(ValueError, match='nonblank'):
        service.dismiss(case.id, cas.id, actor='ca', reason=' ')
    snap = service.dismiss(case.id, cas.id, actor='ca', reason='Awaiting RM; proceed with a draft only')
    assert expected(snap, 1).status == 'Dismissed'
    assert any(e['id'] == cas.id and e['mandatory'] for e in snap.groups['RM'])
    assert 'mandatory gap remains open' in request_list(snap)
    snap = service.restore(case.id, cas.id)
    assert expected(snap, 1).status == 'Missing'
    optional = expected(snap, 11)
    snap = service.dismiss(case.id, optional.id, actor='ca', reason='Not requested for draft')
    assert not any(e['id'] == optional.id for e in snap.groups['internal team'])
    other = make_case(repo)
    with pytest.raises(ValueError, match='another case'):
        service.dismiss(other.id, cas.id, actor='ca', reason='Test isolation')


def test_public_partial_external_and_private_types_never_close_gaps(database):
    repo = Repository(database)
    case = make_case(repo, property_or_asset_security=True, property_income_repayment=True)
    report = public_doc(repo, case, intake={'catalogue_support': [
        {'id': 20, 'coverage': 'full', 'pages': [10]},
        {'id': 9, 'coverage': 'full', 'pages': [50]},
        {'id': 16, 'coverage': 'partial', 'pages': [53]},
        {'id': 1, 'coverage': 'full', 'pages': [1]},
    ]})
    confirm(repo, report)
    public_doc(repo, case, 10, confirmed_by='ca', confirmed_at=NOW)
    snap, sections = refresh(repo, case)
    assert snap.support[20].full
    assert snap.support[9].usable and not snap.support[9].full
    assert snap.support[16].usable and not snap.support[16].full
    assert not snap.support[1].usable and expected(snap, 1).status == 'Missing'
    assert sections[12].readiness == 'Waiting for input'
    assert expected(snap, 10).status == 'Found publicly'
    assert expected(snap, 9).status == 'Found publicly'
    text = request_list(snap)
    assert 'Public search: not run' in text
    assert 'cannot replace' in text
    assert all(e.search_outcome == 'not run' for e in snap.expected)
    internal = doc(repo, case, 10)
    snap, sections = refresh(repo, case)
    assert snap.support[10].full and sections[12].readiness == 'Can draft (full)'
    assert internal.id in expected(snap, 10).document_ids


def test_spread_validation_sources_and_industry_confirmation(database):
    repo = Repository(database)
    case = make_case(repo)
    report = public_doc(repo, case)
    generated = doc(repo, case, 19, origin='generated')
    raw_spread = doc(repo, case, 7, origin='generated')
    snap, _ = refresh(repo, case)
    assert not snap.support[19].full and not snap.support[7].usable
    for status in ('pending', 'invalid', 'manual review'):
        repo.save(s.Spread(case_id=case.id, document_ids=[report.id], version=status,
                           values={}, validation_status=status))
    snap, _ = refresh(repo, case)
    assert not snap.support[7].full
    valid = repo.save(s.Spread(case_id=case.id, document_ids=[report.id], version='mock-valid',
                              values={'fixture': 'SYNTHETIC DEMO DATA'}, validation_status='valid'))
    snap, _ = refresh(repo, case)
    assert snap.support[7].usable and not snap.support[7].full
    assert snap.support[7].spread_ids == [valid.id]
    confirm(repo, report)
    confirm(repo, generated)
    snap, _ = refresh(repo, case)
    assert snap.support[7].full and snap.support[19].full
    assert raw_spread.id in expected(snap, 7).document_ids
    public_doc(repo, case, supersedes_id=report.id, revision=2, period='2027', confirmed_by='ca', confirmed_at=NOW)
    snap, _ = refresh(repo, case)
    assert not snap.support[7].full  # Old spread cannot satisfy a newer source.


def test_conflicts_dedup_search_metadata_and_refresh_persistence(database, tmp_path):
    repo = Repository(database)
    case = make_case(repo, property_or_asset_security=True)
    service = IntakeService(repo, tmp_path / 'blobs')
    content = f'SYNTHETIC DEMO DATA\nValuation report\nBorrower: {case.borrower_name}\nPeriod: 2026-10-31\n'.encode()
    good = service.ingest(case.id, 'valuation.txt', content).document
    snap, sections = refresh(repo, case)
    ids = [e.id for e in snap.expected]
    section_ids = [e.id for e in sections.values()]
    item = expected(snap, 4)
    repo.save(item.model_copy(update={'search_outcome': 'failed', 'search_attempts': [{'outcome': 'failed', 'reason': 'offline fixture'}]}))
    for suffix, metadata in [('wrong', {'entity': 'Wrong borrower'}), ('old', {'period': '2025'})]:
        service.ingest(case.id, f'{suffix}.txt', content + suffix.encode(), metadata=metadata)
    snap, sections = refresh(repo, case)
    assert [e.id for e in snap.expected] == ids
    assert [e.id for e in sections.values()] == section_ids
    assert expected(snap, 9).document_ids == [good.id]
    assert len(snap.support[9].details) == 2
    assert expected(snap, 4).search_outcome == 'failed'
    assert expected(snap, 4).search_attempts[0]['reason'] == 'offline fixture'
    assert service.ingest(case.id, 'again.txt', content).outcome == 'duplicate'
    database.commit()
    database.expunge_all()
    assert len(repo.list_for_case(s.Section, case.id)) == 14
    assert repo.list_for_case(s.Section, case.id)[7].input_fingerprint


def load_saved_public(repo, case):
    root = ROOT / 'demo/public_pack/esr-reit'
    manifest = yaml.safe_load((root / 'manifest.yaml').read_text())
    annual = manifest['documents'][0]
    evidence = {e['topic']: e['pdf_pages'] for e in annual['evidence']}
    source = repo.save(s.Document(case_id=case.id, catalogue_id=4, entity=case.borrower_name,
        period=annual['period_end'], content_hash=annual['sha256'], storage_path=str(root / annual['file']),
        original_filename=annual['file'], origin='public', synthetic=False,
        url=annual['url'], retrieved_at=NOW, intake={'catalogue_support': [
            {'id': 20, 'coverage': 'full', 'pages': evidence['unitholding_structure']},
            {'id': 9, 'coverage': 'partial', 'pages': evidence['portfolio_valuation_and_occupancy']},
            {'id': 16, 'coverage': 'partial', 'pages': evidence['portfolio_lease_expiry']},
        ]}))
    assert sha256(Path(source.storage_path).read_bytes()).hexdigest() == source.content_hash
    for entry in manifest['documents'][1:]:
        repo.save(s.Document(case_id=case.id, suggestion_id='external_rating' if entry['kind'] == 'external_rating_release' else 'public_news',
            entity=case.borrower_name, period=entry.get('period_end', entry['date']),
            content_hash=entry['sha256'], storage_path=str(root / entry['file']), original_filename=entry['file'],
            origin='public', synthetic=False, url=entry['url'], retrieved_at=NOW))
    return source


@pytest.mark.parametrize('route', ['upload', 'folder'])
def test_three_actual_synthetic_tranches_with_saved_public_and_mock_spread(database, tmp_path, route):
    repo = Repository(database)
    pack = ROOT / 'demo/synthetic'
    case_data = yaml.safe_load((pack / 'case.yaml').read_text())
    case = make_case(repo, borrower_name=case_data['borrower']['name'], **case_data['app_case'])
    manifest = yaml.safe_load((pack / 'manifest.yaml').read_text())
    folders = {str(i): pack / f'tranche_{i}' for i in (1, 2, 3)}
    intake = IntakeService(repo, tmp_path / 'blobs', folders)
    for tranche in (1, 2, 3):
        entries = [e for e in manifest['documents'] if e.get('tranche') == tranche]
        hints = {}
        for entry in entries:
            path = pack / entry['file']
            hint = dict(entity=entry['entity'], period=entry.get('period_end', entry['date']), synthetic=True)
            hint.update({'catalogue_id': entry['catalogue_id']} if entry.get('catalogue_id') else {'suggestion_id': entry['suggestion_id']})
            hints[path.name] = hint
            if route == 'upload':
                result = intake.ingest(case.id, path.name, path.read_bytes(), metadata=hint)
                assert result.document.conflict_status == 'none', result.explanations
        if route == 'folder':
            # Use manifest directory names rather than assuming pack layout.
            intake.folders[str(tranche)] = (pack / entries[0]['file']).parent.resolve()
            results = intake.scan(case.id, str(tranche), hints)
            assert len(results) == len(entries)
            assert all(r.document.conflict_status == 'none' for r in results)
        if tranche == 1:
            source = load_saved_public(repo, case)
            confirm(repo, source)
            confirm(repo, doc(repo, case, 19, origin='generated'))
            repo.save(s.Spread(case_id=case.id, document_ids=[source.id], version='G1-mock-saved-output',
                              values={'fixture': 'SYNTHETIC DEMO DATA — readiness seam only'}, validation_status='valid'))
        snap, sections = refresh(repo, case)
        if tranche == 1:
            assert all(sections[i].completeness != 'none' for i in (4, 5, 6, 7, 10))
            assert all(sections[i].readiness == 'Can draft (partial)' for i in (8, 9))
            assert sections[11].readiness == sections[12].readiness == sections[13].readiness == 'Waiting for input'
            assert {9, 13, 15, 16} <= {e['catalogue_id'] for e in snap.groups['client']}
            assert {3, 10, 17, 21, 22} <= {e['catalogue_id'] for e in snap.groups['internal team']}
        elif tranche == 2:
            assert all(sections[i].readiness == 'Can draft (full)' for i in (1, 2, 3, 8, 9, 11))
            assert sections[12].readiness == sections[13].readiness == sections[14].readiness == 'Waiting for input'
        else:
            assert all(sections[i].readiness == 'Can draft (full)' for i in range(1, 14))
            assert sections[14].readiness == 'Waiting for input'
            repo.save(case.model_copy(update={'ca_position': 'SYNTHETIC DEMO DATA — CA supports proposed facilities subject to stated conditions.'}))
            snap, sections = refresh(repo, case)
            assert sections[14].readiness == 'Can draft (full)'
            assert not [e for items in snap.groups.values() for e in items if e['mandatory']]
    assert all(d.synthetic for d in repo.list_for_case(s.Document, case.id) if d.origin in {'upload', 'folder'})


@pytest.mark.parametrize('actual_pack', [False, True])
def test_drafted_confirmed_stale_states_preserve_versions_and_gaps(database, tmp_path, actual_pack):
    repo = Repository(database)
    case = make_case(repo, property_or_asset_security=True, borrower_name='ESR-REIT')
    term = doc(repo, case, 2)
    def valuation_input(revised=False, supersedes=None):
        if not actual_pack:
            return doc(repo, case, 9, **(dict(revision=2, supersedes_id=supersedes.id,
                period='2026-11-09') if revised else {}))
        relative = 'late_update/valuation_v2.pdf' if revised else 'tranche_2/valuation_v1.pdf'
        path = ROOT / 'demo/synthetic' / relative
        return IntakeService(repo, tmp_path / 'blobs').ingest(case.id, path.name, path.read_bytes(),
            metadata=dict(entity=case.borrower_name, catalogue_id=9, synthetic=True,
                          period='2026-11-09' if revised else '2026-10-31')).document
    valuation = valuation_input()
    _, sections = refresh(repo, case)
    template = repo.save(s.TemplateVersion(team_id='fig', display_version='test',
        content_hash='e' * 64, storage_path='runtime/test-template.docx'))
    originals = {}
    for section_id in (7, 8, 11, 14):
        section = sections[section_id]
        draft = repo.save(s.DraftVersion(case_id=case.id, section_id=section_id,
            text='SYNTHETIC DEMO DATA — CA-edited wording must survive.', ca_edits=True,
            config_hash=case.config_hash, prompt_version='test', model_version='mock',
            template_version_id=template.id, input_fingerprint=section.input_fingerprint,
            author='ca', document_ids=[term.id, valuation.id]))
        originals[section_id] = draft
        repo.save(section.model_copy(update={'current_draft_id': draft.id}))
    _, sections = refresh(repo, case)
    assert all(sections[i].readiness == 'Drafted' for i in originals)
    assert sections[7].completeness == 'partial' and sections[7].gaps
    for i, draft in originals.items():
        repo.save(sections[i].model_copy(update={'confirmed_draft_id': draft.id}))
    _, sections = refresh(repo, case)
    assert all(sections[i].readiness == 'CA confirmed' for i in originals)
    revised = valuation_input(True, valuation)
    assert revised.supersedes_id == valuation.id and revised.revision == 2
    _, sections = refresh(repo, case)
    assert sections[7].readiness == 'CA confirmed'
    assert all(sections[i].readiness == 'Stale' for i in (8, 11, 14))
    for i, draft in originals.items():
        assert repo.get(s.DraftVersion, draft.id) == draft
        assert sections[i].current_draft_id == sections[i].confirmed_draft_id == draft.id
    # Refresh is stable and never manufactures a new draft or version.
    assert refresh(repo, case)[1] == sections
    assert len(repo.list_for_case(s.DraftVersion, case.id)) == 4


def test_all_seven_exact_status_names_are_exercised(database):
    repo = Repository(database)
    case = make_case(repo)
    doc(repo, case, 2)
    public_doc(repo, case)
    snap, _ = refresh(repo, case)
    snap = GapService(repo).dismiss(case.id, expected(snap, 1).id, actor='ca', reason='Awaiting RM')
    assert {e.status for e in snap.expected} == {
        'Provided', 'Found publicly', 'Can generate', 'Missing', 'Suggested', 'Not applicable', 'Dismissed'}


def test_pinned_pre_b05_configuration_hash_survives_optional_rule_extension(database):
    repo = Repository(database)
    # Reconstruct the B01 snapshot shape (all original defaults were serialized).
    data = load_team('fig').model_dump(mode='json')
    for item in data['catalogue']['items']:
        item.pop('generation')
        item.pop('generation_inputs')
    data['rules'].pop('draft_gates')
    data['rules']['suggestions'] = [item for item in data['rules']['suggestions'] if item['id'] != 'prior_condition_evidence']
    for item in data['rules']['suggestions']:
        for field in ('owner_group', 'when', 'trigger_catalogue_ids', 'reason'):
            item.pop(field)
    digest = sha256(json.dumps(data, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    config = TeamConfig.model_validate(data)
    assert config.content_hash == digest
    case = make_case(repo, config_snapshot=data, config_hash=digest)
    repo.save(case.model_copy(update={'ca_position': 'SYNTHETIC DEMO DATA — stated CA position'}))
    refresh(repo, case)
    assert repo.get(s.Case, case.id).config_snapshot == data
    assert repo.get(s.Case, case.id).config_hash == digest


def test_alternate_config_drives_readiness_without_fig_id_branching(database):
    config = load_team('fig').model_dump(mode='json')
    config['template']['team_id'] = 'alternate'
    config['template']['sections'][0]['name'] = 'Test alternate request'
    config['catalogue']['items'][0]['owner_group'] = 'client'
    config['catalogue']['items'][0]['mandatory_when'] = {'op': 'not', 'args': [{'op': 'always'}]}
    alternate = TeamConfig.model_validate(config)
    repo = Repository(database, config_loader=lambda team: alternate)
    case = repo.save(s.Case(borrower_name='SYNTHETIC DEMO DATA — Alternate', team_id='alternate',
        config_version=alternate.template.version, config_hash=alternate.content_hash,
        case_type='new', borrower_type='reit', existing_client=False, new_to_bank=True))
    doc(repo, case, 2)
    snap, sections = refresh(repo, case)
    assert sections[1].readiness == 'Can draft (full)'
    assert expected(snap, 1).usual_owner == 'client' and not expected(snap, 1).mandatory


def request_text(app, path):
    import asyncio
    messages = []
    async def receive():
        return {'type': 'http.request', 'body': b'', 'more_body': False}
    async def send(message):
        messages.append(message)
    asyncio.run(app({'type': 'http', 'asgi': {'version': '3.0'}, 'http_version': '1.1',
        'method': 'GET', 'scheme': 'http', 'path': path, 'raw_path': path.encode(),
        'query_string': b'', 'headers': [], 'server': ('test', 80),
        'client': ('test', 1), 'root_path': ''}, receive, send))
    return messages[0], b''.join(m.get('body', b'') for m in messages[1:]).decode()


def test_readiness_api_export_dismiss_restore_and_boundaries(tmp_path):
    engine, sessions = create_database(tmp_path / 'readiness-api.sqlite')
    try:
        with sessions.begin() as session:
            case = make_case(Repository(session))
        app = create_app(sessions=sessions, storage_root=tmp_path / 'blobs')
        path = f'/cases/{case.id}'
        status, data = request(app, 'GET', path + '/readiness')
        assert status == 200 and len(data['sections']) == 14
        cas = next(e for e in data['expected_documents'] if e['catalogue_id'] == 1)
        target = path + f'/expected-documents/{cas["id"]}'
        payload = {'actor': 'demo-ca', 'reason': 'SYNTHETIC DEMO DATA — waiting for RM'}
        assert request(app, 'POST', target + '/dismiss', json.dumps(payload | {'role': 'Credit Head'}).encode())[0] == 403
        assert request(app, 'POST', target + '/dismiss', json.dumps(payload | {'reason': ' '}).encode())[0] == 422
        status, dismissed = request(app, 'POST', target + '/dismiss', json.dumps(payload).encode())
        assert status == 200 and any(e['status'] == 'Dismissed' for e in dismissed['expected_documents'])
        message, text = request_text(app, path + '/request-list')
        assert message['status'] == 200 and b'text/plain' in dict(message['headers'])[b'content-type']
        assert all(owner in text for owner in ('RM', 'client', 'internal team'))
        assert 'mandatory gap remains open' in text and 'Public search: not run' in text
        assert payload['reason'] in text
        status, restored = request(app, 'POST', target + '/restore', json.dumps(payload).encode())
        assert status == 200 and not any(e['status'] == 'Dismissed' for e in restored['expected_documents'])
        assert request(app, 'GET', '/cases/unknown/readiness')[0] == 404
        assert request(create_app(), 'GET', path + '/readiness')[0] == 503
    finally:
        engine.dispose()


@pytest.mark.parametrize('origin', ['upload', 'generated'])
def test_unvalidated_spread_file_does_not_supply_computed_inputs(database, origin):
    repo = Repository(database)
    case = make_case(repo)
    doc(repo, case, 7, origin=origin)
    snap, sections = refresh(repo, case)
    assert expected(snap, 7).status == 'Provided'
    assert not snap.support[7].usable and not snap.support[7].full
    assert sections[10].readiness == 'Waiting for input'


def test_unconfirmed_public_drafts_partial_and_bad_mappings_are_ignored(database):
    repo = Repository(database)
    case = make_case(repo)
    report = public_doc(repo, case, intake={'catalogue_support': [{'id': 20, 'coverage': 'full', 'pages': [10]}]})
    snap, sections = refresh(repo, case)
    assert sections[5].readiness == 'Can draft (partial)'
    confirm(repo, report)
    assert refresh(repo, case)[1][5].readiness == 'Can draft (full)'
    other = make_case(repo)
    public_doc(repo, other, confirmed_by='ca', confirmed_at=NOW,
               intake={'catalogue_support': [{'id': 20, 'coverage': 'full', 'pages': []}]})
    snap, sections = refresh(repo, other)
    assert not snap.support[20].usable and sections[5].readiness == 'Can draft (partial)'


@pytest.mark.parametrize('mutation', [
    lambda d: d['catalogue']['items'][6]['generation_inputs'].append(999),
    lambda d: d['rules']['draft_gates'][0]['any_inputs'].append(999),
    lambda d: d['rules']['suggestions'][-1]['trigger_catalogue_ids'].append(999),
])
def test_bad_readiness_config_references_fail(mutation):
    from pydantic import ValidationError
    data = load_team('fig').model_dump(mode='json')
    mutation(data)
    with pytest.raises(ValidationError):
        TeamConfig.model_validate(data)
