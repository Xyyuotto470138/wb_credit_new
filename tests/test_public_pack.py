"""Offline integrity and provenance checks for the curated task-0002 evidence."""
from datetime import date
import hashlib
from pathlib import Path
import socket
import unicodedata
from urllib.parse import urlparse

import fitz
import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
MANIFESTS = [ROOT / 'demo/public_pack/esr-reit/manifest.yaml',
             ROOT / 'demo/research/manifest.yaml']
PACK = yaml.safe_load(MANIFESTS[0].read_text())
RECORDS = [(path, item) for path in MANIFESTS
           for item in yaml.safe_load(path.read_text())['documents']]


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setenv('LLM_PROVIDER', 'mock')

    def forbidden(*args, **kwargs):
        raise AssertionError('Public-pack tests must not use the network')

    monkeypatch.setattr(socket.socket, 'connect', forbidden)
    monkeypatch.setattr(socket.socket, 'connect_ex', forbidden)
    monkeypatch.setattr(socket, 'create_connection', forbidden)
    monkeypatch.setattr(socket, 'getaddrinfo', forbidden)


def normalized(value):
    return ' '.join(unicodedata.normalize('NFKC', value).casefold().split())


@pytest.mark.parametrize('manifest,item', RECORDS, ids=[d['id'] for _, d in RECORDS])
def test_saved_document_integrity_and_page_evidence(manifest, item):
    for key in ('id', 'file', 'catalogue_type', 'title', 'url', 'publisher',
                'date', 'retrieved_at', 'pages', 'sha256', 'entity', 'evidence'):
        assert item[key], (item['id'], key)
    assert urlparse(item['url']).scheme == 'https'
    assert date.fromisoformat(item['date']) <= date.fromisoformat(item['retrieved_at'])
    if 'period_end' in item:
        assert date.fromisoformat(item['period_end']) <= date.fromisoformat(item['date'])
    assert item['origin'] == 'public' and item['synthetic'] is False
    assert item['ca_confirmed'] is False
    path = (manifest.parent / item['file']).resolve()
    assert path.is_relative_to(manifest.parent.resolve())
    data = path.read_bytes()
    assert data.startswith(b'%PDF-'), 'Reject empty downloads and HTML error pages'
    assert len(data) == item['bytes']
    assert hashlib.sha256(data).hexdigest() == item['sha256']
    with fitz.open(path) as pdf:
        assert len(pdf) == item['pages']
        text = normalized(' '.join(page.get_text() for page in pdf))
        # OUE's old legal name is used in the original rating announcement.
        aliases = [item['entity']]
        if item['entity'] == 'OUE REIT':
            aliases += ['OUE Commercial Real Estate Investment Trust']
        assert any(normalized(alias) in text for alias in aliases)
        for evidence in item['evidence']:
            pages = evidence['pdf_pages']
            assert pages and all(1 <= n <= len(pdf) for n in pages)
            assert len(pages) == len(evidence['printed_pages'])
            cited = normalized(' '.join(pdf[n - 1].get_text() for n in pages))
            for term in evidence['check_terms']:
                assert normalized(term) in cited, (item['id'], evidence['topic'], term)


def test_recommended_pack_scope_and_required_sources():
    documents = PACK['documents']
    assert PACK['borrower']['name'] == 'ESR-REIT'
    assert PACK['ca_confirmation_required'] is True
    assert all(d['entity'] == 'ESR-REIT' for d in documents)
    assert len({d['id'] for d in documents}) == len(documents)
    assert len({d['file'] for d in documents}) == len(documents)
    assert sum(d['kind'] == 'exchange_announcement' for d in documents) == 3
    annual = next(d for d in documents if d['kind'] == 'annual_report')
    assert annual['period_end'] == '2025-12-31'
    assert annual['pages'] == 244
    assert {6, 9, 16, 20} <= {s['id'] for s in annual['catalogue_support']}
    topics = {e['topic']: e for e in annual['evidence']}
    assert topics['trust_structure']['as_of'] == '2025-12-31'
    assert topics['unitholding_structure']['as_of'] == '2026-03-19'
    rating = next(d for d in documents if d['kind'] == 'external_rating_release')
    assert rating['satisfies_internal_rating'] is False
    assert rating['catalogue_type']['scope'] == 'external_only'
    with fitz.open(MANIFESTS[0].parent / rating['file']) as pdf:
        assert 'Fitch Ratings - Singapore' in pdf[1].get_text()
    update = next(d for d in documents if d['kind'] == 'business_update')
    assert update['period_end'] == '2026-09-30'
    assert update['date'] == '2026-10-27'
    assert update['catalogue_type']['id'] is None
    assert PACK['unfilled_private_inputs']


def test_all_saved_pdfs_are_manifested():
    listed = {(path.parent / d['file']).resolve() for path, d in RECORDS}
    # The Keppel REIT pack (new-to-bank demo case) has its own manifest; its files must be listed there.
    keppel = ROOT / 'demo/public_pack/keppel-reit/manifest.yaml'
    listed |= {(keppel.parent / d['file']).resolve() for d in yaml.safe_load(keppel.read_text())['documents']}
    # B03 owns demo/synthetic and validates its separate synthetic manifest.
    actual = {p.resolve() for folder in ('demo/public_pack', 'demo/research')
              for p in (ROOT / folder).rglob('*.pdf')}
    assert actual == listed
