"""Reviewed fixture operands; Python renders amounts and calculates ratios.

Bindings are authored alongside exact hash/page/quote fixtures, never supplied by
models. Dates, source periods and identifiers remain cited source metadata.
"""
from decimal import Decimal
import re

from .. import schemas as s, models
from ..retrieval.service import identity

VERSION = 'reviewed-draft-values-v1'


def bind(service, case, claim, source):
    values, ids = {}, []
    for name, spec in claim.get('numbers', {}).items():
        quote = ' '.join(spec['quote'].split())
        excerpt = ' '.join(source['excerpt'].split())
        token = spec['token']
        if quote not in excerpt or not re.search(r'(?<![\d.,])' + re.escape(token) + r'(?![\d.,])', quote):
            raise ValueError('numeric operand quote/token mismatch')
        values[name] = Decimal(token.replace(',', ''))
    for name, spec in claim.get('numbers', {}).items():
        value = values[name]
        operands = {name: value}
        if spec.get('op') == 'ratio_percent':
            operands = {key: values[key] for key in spec['operands']}
            a, b = operands.values()
            if b <= 0:
                raise ValueError('nonpositive denominator')
            value = a / b * 100
        elif spec.get('op') == 'ltv_headroom':
            operands = {key: values[key] for key in spec['operands']}
            limit, debt, security = operands.values()
            if security <= 0:
                raise ValueError('nonpositive denominator')
            value = limit - debt / security * 100
        elif spec.get('op') == 'share_of_sum':
            operands = {key: values[key] for key in spec['operands']}
            denominator = sum(operands.values())
            if denominator <= 0 or spec['numerator'] not in operands:
                raise ValueError('invalid share denominator/numerator')
            value = operands[spec['numerator']] / denominator * 100
        elif spec.get('op') == 'subtract':
            operands = {key: values[key] for key in spec['operands']}
            a, b = operands.values()
            value = a - b
        elif spec.get('op') not in (None, 'reported'):
            raise ValueError('unsupported fixture operation')
        ref = identity(VERSION, case.id, source['evidence_id'], claim['id'], name, spec)
        record = s.ComputedValue(id=ref, case_id=case.id, metric='draft/' + claim['id'] + '/' + name,
            formula_version=VERSION + ':' + spec.get('op', 'reported'), operands=operands,
            operand_evidence_ids={key: [source['evidence_id']] for key in operands},
            unit=spec['unit'], currency=spec.get('currency'), period=spec.get('period', source['period']),
            scope=spec.get('scope', case.borrower_name), value=value, validated=True,
            synthetic=source['synthetic'])
        # IDs include the immutable source and reviewed binding, allowing reuse on redraft.
        if not service.repo.session.get(models.ComputedValue, ref):
            service.repo.save(record)
            service.repo.save(s.Citation(id=identity(ref, source['evidence_id']), case_id=case.id,
                evidence_id=source['evidence_id'], computed_value_id=ref, claim_or_cell=record.metric))
        else:
            # Redrafts/comparisons reuse the persisted snapshot, including its
            # creation time; a freshly constructed timestamp is not new evidence.
            record = service.repo.get(s.ComputedValue, ref)
        ids.append(ref)
        if claim.get('financial_cell', {}).get('operand') == name:
            claim['reviewed_value'] = record.model_dump(mode='json')
        claim['text'] = claim['text'].replace('{' + name + '}', format(value, spec.get('format', 'f')))
    if ids:
        claim['computed_value_ids'] = ids
    return claim
