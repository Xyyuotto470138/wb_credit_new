"""0020a: actual saved-pack coverage and immutable numerical write-up bindings."""
import pytest
from pathlib import Path


from backend.app import schemas as s
from test_drafting import setup, generate
from test_synthesis import prerequisites
from test_versions import revised_valuation, versions, command
from backend.app.services.versions import RedraftRequest


@pytest.mark.slow
def test_credit_writeup_all_sections_and_late_ltv(setup):
    service, case = setup
    drafts = prerequisites(service, case)
    drafts[14] = generate(service, case, 14, ca_position='Defer pending a supported repayment plan.')
    for sid, draft in drafts.items():
        assert draft['claim_spans'][0]['template_subparts']
        assert not any('quote mismatch' in g or 'operand quote/token mismatch' in g for g in draft['gaps']), (sid, [g for g in draft['gaps'] if 'mismatch' in g])
        for claim in draft['claim_spans'][1:]:
            assert '{' not in claim['text'], (sid, claim['id'], claim['text'])
            for ref in claim.get('computed_value_ids', []):
                value = service.repo.get(s.ComputedValue, ref)
                assert value.validated and value.case_id == case.id
                assert {e for refs in value.operand_evidence_ids.values() for e in refs} <= set(claim['evidence_ids'])
        assert 'The proposal remains subject to human credit review' not in draft['text']
        assert 'Python debt-service comparisons' not in draft['text']
    assert 'from SGD 45.00 million to SGD 60.00 million' in drafts[1]['text']
    assert 'from SGD 10.00 million to SGD 15.00 million' in drafts[1]['text']
    assert '30 November 2029' in drafts[1]['text'] and 'capital expenditure buffer' in drafts[1]['text']
    assert 'current classification as Pass' in drafts[1]['text'] and 'current DPD of 0' in drafts[1]['text']
    assert '4.4 years' in drafts[4]['text'] and '91.1%' in drafts[4]['text']
    assert '53.57% LTV' in drafts[8]['text'] and '1.43 percentage points' in drafts[8]['text']
    assert 'Demo Insurer' in drafts[8]['text'] and '90.00 million' in drafts[8]['text']
    assert '0.90 percentage points' in drafts[10]['text'] and '0.60x' in drafts[10]['text']
    assert '51.72%' in drafts[9]['text'] and '49.80%' in drafts[9]['text']
    assert 'Demo Tenant B' in drafts[9]['text'] and 'Demo Tenant C' in drafts[9]['text']
    assert 'Perpetual (Asia) Limited' in drafts[4]['text']
    assert 'Fitch' in drafts[12]['text'] and '28 October 2025' in drafts[12]['text']
    assert 'Property-only repayment is insufficient' in drafts[14]['text']
    assert drafts[14]['claim_spans'][1]['text'].endswith('Defer pending a supported repayment plan.')
    old = drafts[8]
    revised_valuation(service, case)
    new = versions(service).redraft(case.id, 8, command(service, case, 8, RedraftRequest, confirm_unsecured=True))
    assert '57.69% LTV' in new['text'] and '-2.69 percentage points' in new['text']
    assert '53.57% LTV' not in new['text']
    assert service.get(case.id, old['id']) == old
    out = Path('runtime/0020a');out.mkdir(exist_ok=True)
    for sid, draft in drafts.items():
        (out / f'section-{sid}.txt').write_text(draft['text'])
    (out / 'revised-security.txt').write_text(new['text'])


def test_numeric_quote_rejection_preserves_other_supported_claims(setup):
    service, case = setup
    claim = next(c for c in service.fixture['claims'] if c['id'] == 'request-limits')
    claim['numbers']['old_tl']['token'] = '999'
    draft = generate(service, case, 1)
    assert '999' not in draft['text']
    assert not any(c.get('id') == 'request-limits' for c in draft['claim_spans'])
    assert any('numeric operand quote/token mismatch' in g for g in draft['gaps'])
    assert any(c.get('id') == 'request' for c in draft['claim_spans'])
