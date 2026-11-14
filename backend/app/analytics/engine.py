"""Pure Decimal arithmetic. No provider, source lookup, inferred defaults or eval."""
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation, localcontext, ROUND_HALF_UP
import re

D = Decimal
VERSION = 'computed-tables-v1'


def number(text):
    text = str(text).strip().replace(',', '')
    if re.fullmatch(r'\(\d+(?:\.\d+)?\)', text):
        text = '-' + text[1:-1]
    if not re.fullmatch(r'-?\d+(?:\.\d+)?', text):
        raise ValueError('Missing or nonnumeric source operand')
    value = D(text)
    if not value.is_finite() or len(value.as_tuple().digits) > 30:
        raise ValueError('Nonfinite or oversized operand')
    return value


@dataclass
class Fact:
    value: Decimal
    unit: str
    currency: str | None
    period: str
    scope: str
    basis: str
    refs: list[str]
    synthetic: bool = False
    proxy: bool = False
    item: str | None = None
    maturity: date | None = None
    source: dict = field(default_factory=dict)


def normalize(value, unit):
    factor, canonical = {'currency_thousand': (D(1000), 'currency'),
        'currency_million': (D(1000000), 'currency'),
        'cents/unit': (D('.01'), 'currency/unit'), 'fraction': (D(100), 'percent')}.get(unit, (D(1), unit))
    return value * factor, canonical


def display(value):
    return None if value is None else str(value.quantize(D('.000001'), rounding=ROUND_HALF_UP))


def calculate(metric, inputs, period, scope):
    flat = {f'{name}.{i}': f for name, facts in inputs.items() for i, f in enumerate(facts)}
    result = dict(metric=metric.id, name=metric.name, unit=metric.unit, period=period, scope=scope,
        currency=None, value=None, display=None, gaps=[], thresholds=[], details={},
        synthetic=any(f.synthetic for f in flat.values()), proxy=any(f.proxy for f in flat.values()),
        operands={k: str(f.value) for k, f in flat.items()},
        operand_evidence_ids={k: f.refs for k, f in flat.items()},
        sources={k: f.source for k, f in flat.items()}, formula=metric.formula.model_dump(mode='json'))
    def require(ok, message):
        if not ok:
            raise ValueError(message)
    try:
        names = metric.formula.operands
        reported_fallback = set(inputs) == {'reported'} and metric.reported_fallback
        if reported_fallback:
            names = ['reported']
        require(set(inputs) <= set(names) | ({metric.reconcile_to} if metric.reconcile_to else set()), 'Unknown operand mapping')
        require(all(inputs.get(n) for n in names), 'Missing operands: ' + ', '.join(n for n in names if not inputs.get(n)))
        require(all(f.period == period and f.scope == scope for f in flat.values()), 'Mismatched period or scope')
        currencies = {f.currency for f in flat.values() if f.unit.startswith('currency')}
        require(None not in currencies and len(currencies) <= 1, 'Mixed or missing currency; supply sourced conversion before calculation')
        result['currency'] = next(iter(currencies), None)
        for name, facts in inputs.items():
            expected = metric.unit if reported_fallback else metric.input_units.get(name)
            require(expected is not None and all(f.unit == expected for f in facts), f'{name}: incompatible or unspecified unit')
            if metric.required_basis:
                require(all(f.basis == metric.required_basis for f in facts), f'{name}: missing verified definition/basis {metric.required_basis}')
            if metric.allowed_bases:
                require(all(f.basis in metric.allowed_bases for f in facts), f'{name}: unsupported weighting basis')
            require(all(f.refs for f in facts), f'{name}: missing source')
        if metric.thresholds or metric.forbid_proxy:
            require(not result['proxy'], 'Proxy inputs cannot drive regulatory measures, sensitivity or valuation rates')
        if metric.nonnegative:
            require(all(f.value >= 0 for f in flat.values()), 'Negative operand is incompatible with this definition')
        def scalar(n):
            require(len(inputs[n]) == 1, f'{n}: expected one sourced value')
            return inputs[n][0].value
        def divide(a, b):
            require(b > 0, 'Missing, zero or negative denominator')
            return a / b
        op = 'reported' if reported_fallback else metric.formula.op
        if reported_fallback:
            result['formula'] = {'op': 'reported', 'operands': ['reported']}
        with localcontext() as context:
            context.prec = 38
            if op == 'reported':
                value = scalar(names[0])
            elif op == 'ratio':
                value = divide(scalar(names[0]), scalar(names[1])) * D(metric.multiplier)
            elif op == 'subtract':
                value = scalar(names[0]) - scalar(names[1])
            elif op == 'sum':
                value = sum((f.value for n in names for f in inputs[n]), D(0))
                ids = [f.item for n in names for f in inputs[n]]
                require(all(ids) and len(ids) == len(set(ids)), 'Sum requires unique item identities; duplicate or unknown asset')
            elif op == 'weighted_average':
                a, b = inputs[names[0]], inputs[names[1]]
                keys = [f.item for f in a]
                weights = {f.item: f for f in b}
                require(all(keys) and len(keys) == len(set(keys)) and len(weights) == len(b) and set(keys) == set(weights), 'Weights must match unique item identities')
                require(len({f.basis for f in a+b}) == 1, 'Incompatible weighting bases')
                require(sum((f.value for f in b), D(0)) == 100, 'Percentage weights must cover the complete portfolio (100%)')
                value = divide(sum((f.value * weights[f.item].value for f in a), D(0)), sum((f.value for f in b), D(0)))
            elif op == 'bucket_sum':
                # Second operand is the reported total, not numeric encodings of dates.
                a = inputs[names[0]]
                as_of = date.fromisoformat(period)
                require(all(f.maturity and f.item for f in a) and len({f.item for f in a}) == len(a), 'Maturity dates and unique debt identities required')
                buckets = {}
                for f in a:
                    require(f.maturity >= as_of, 'Debt maturity precedes reporting date')
                    key = str(f.maturity.year)
                    buckets[key] = buckets.get(key, D(0)) + f.value
                value = sum((f.value for f in a), D(0))
                require(value == scalar(names[1]), 'Maturity buckets do not reconcile to total debt')
                result['details']['buckets'] = {k: str(v) for k, v in sorted(buckets.items())}
            elif op == 'ebitda_stress':
                value = divide(scalar(names[0]) * D('.9'), scalar(names[1]))
            elif op == 'interest_stress':
                # Full debt exposure includes fixed and hedged loans (MAS response 3.10).
                value = divide(scalar(names[0]), scalar(names[1]) + scalar(names[2]) * D('.01'))
            else:
                raise ValueError('Unsupported calculation')
            if metric.reconcile_to and not reported_fallback:
                require(inputs.get(metric.reconcile_to), f'Missing reconciliation operand: {metric.reconcile_to}')
                require(abs(value - scalar(metric.reconcile_to)) <= D(metric.tolerance), 'Computed value does not reconcile to reported figure')
            if metric.minimum is not None:
                require(value >= D(metric.minimum), 'Computed value below valid range')
            if metric.maximum is not None:
                require(value <= D(metric.maximum), 'Computed value above valid range')
            result.update(value=str(value), display=display(value))
            for rule in metric.thresholds:
                require(rule.verification != 'pending B10', 'Rule verification pending for pinned configuration')
                require(period >= rule.effective_date, 'Threshold not effective for reporting period')
                limit = D(rule.value)
                headroom = limit-value if rule.comparison == 'maximum' else value-limit
                result['thresholds'].append(dict(limit=rule.value, comparison=rule.comparison,
                    headroom=None if rule.comparison == 'flag_below' else str(headroom),
                    headroom_unit='percentage points' if metric.unit == 'percent' else metric.unit,
                    status=('improvement plan expected' if value < limit else 'not triggered') if rule.comparison == 'flag_below'
                        else ('outside configured threshold' if headroom < 0 else 'within configured threshold'),
                    source=rule.source, effective_date=rule.effective_date, verification=rule.verification))
    except (ValueError, InvalidOperation) as error:
        result.update(value=None, display=None, thresholds=[], gaps=[f'{metric.name}: {error}'])
    return result
