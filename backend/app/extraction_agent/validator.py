"""Adapted 2026-11-10 from Phase 1 extraction_agent/validator.py.

Retains completeness, statement arithmetic and cross-statement validation. Replaces
keyword/row-count confidence with exact configured aliases, Decimal, all periods,
source column checks, and explicit failed/skipped outcomes. No missing-as-zero.
"""
from decimal import Decimal, InvalidOperation, localcontext
import re

from .contracts import Extraction

VERSION = 'spread-validation-v1'
NUMBER = re.compile(r'^[+-]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?$')


def compact(text):
    return ' '.join(text.split())


def contains_quote(quote, text):
    return bool(re.search(r'(?<!\S)' + re.escape(compact(quote)) + r'(?!\S)', compact(text)))


def number(raw):
    raw = raw.strip()
    if len(raw) > 50 or sum(c.isdigit() for c in raw) > 30:
        raise ValueError('Numeric token exceeds supported precision')
    if raw in {'–', '—', '-', 'N/A', 'n/a', ''}:
        return None
    negative = raw.startswith('(') and raw.endswith(')')
    raw = raw[1:-1] if negative else raw
    if not NUMBER.fullmatch(raw):
        raise ValueError('Unsupported numeric token')
    value = Decimal(raw.replace(',', ''))
    if negative and value < 0:
        raise ValueError('Ambiguous negative token')
    return value.copy_negate() if negative else value


def issue(check, statement, message, *, outcome='failed', **details):
    return dict(check=check, statement=statement, message=message, outcome=outcome, **details)


def context_errors(table, sources, profile):
    errors = []
    source = sources.get(table.evidence_id)
    currency_source = sources.get(table.currency_evidence_id)
    if not source or not currency_source:
        return ['Unknown or out-of-selection evidence reference']
    if source['document_id'] != currency_source['document_id']:
        errors.append('Currency declaration must belong to the same document version')
    text = compact(source['excerpt'])
    for quote in [table.header_quote, table.scope_quote, table.unit_quote]:
        if not contains_quote(quote, text):
            errors.append('Table context quote not present in cited source')
    if not contains_quote(table.currency_quote, currency_source['excerpt']):
        errors.append('Currency quote not present in cited source')
    if not any(alias.casefold() in table.currency_quote.casefold()
               for alias in profile.currencies.get(table.currency, [])):
        errors.append('Currency declaration is not supported')
    if re.findall(r'\b20\d{2}\b', table.header_quote) != [c.period for c in table.columns]:
        errors.append('Period columns do not match source header order')
    scopes = []
    for col in table.columns:
        if col.scope not in profile.scopes:
            errors.append('Unknown configured scope')
        if not scopes or scopes[-1] != col.scope:
            scopes.append(col.scope)
    if compact(table.scope_quote).casefold() != ' '.join(scopes).casefold():
        errors.append('Scope columns do not match source header order')
    if len({(c.period, c.scope) for c in table.columns}) != len(table.columns):
        errors.append('Duplicate period/scope column')
    if table.unit not in profile.units or compact(table.unit_quote) != table.unit:
        errors.append('Unknown or mismatched reported unit')
    return list(dict.fromkeys(errors))


def validate_extraction(extraction: Extraction, sources, profile, periods, scope):
    with localcontext() as context:
        context.prec = 64
        return _validate(extraction, sources, profile, periods, scope)


def _validate(extraction: Extraction, sources, profile, periods, scope):
    issues, facts, passed, checks = [], [], [], []
    aliases = {(a.statement, compact(alias).casefold()): code
               for code, a in profile.accounts.items() for alias in a.aliases}
    for table in extraction.tables:
        errors = context_errors(table, sources, profile)
        if errors:
            issues.extend(issue('source_context', table.statement, e) for e in errors)
            continue
        source = sources[table.evidence_id]
        for row in table.rows:
            code = aliases.get((table.statement, compact(row.label).casefold()))
            if not code:
                issues.append(issue('mapping', table.statement, f'Unmapped row: {row.label}', outcome='skipped'))
                continue
            expected = compact(' '.join([row.label, row.note, *row.values]))
            if (len(row.values) != len(table.columns) or compact(row.quote) != expected
                    or compact(row.quote) not in {compact(line) for line in source['excerpt'].splitlines()}):
                issues.append(issue('source_row', table.statement, f'Row/column transcription not supported: {row.label}'))
                continue
            for col, raw in zip(table.columns, row.values):
                if col.period not in periods or col.scope != scope:
                    continue
                try:
                    value = number(raw)
                except (ValueError, InvalidOperation):
                    issues.append(issue('numeric_token', table.statement, f'Invalid number: {row.label}'))
                    continue
                if value is None:
                    issues.append(issue('missing_value', table.statement,
                        f'{code}/{col.period}/{scope}: reported dash/unknown needs review', outcome='skipped'))
                    continue
                scale = Decimal(profile.units[table.unit])
                facts.append(dict(metric=code, statement=table.statement, period=col.period,
                    scope=scope, currency=table.currency, unit='currency', value=str(value * scale),
                    raw_value=raw, scale=str(scale), reported_unit=table.unit,
                    evidence_ids=list(dict.fromkeys([table.evidence_id, table.currency_evidence_id])),
                    quote=row.quote, synthetic=any(sources[e]['synthetic'] for e in
                        [table.evidence_id, table.currency_evidence_id])))
    keyed = {}
    for fact in facts:
        key = (fact['metric'], fact['period'])
        keyed.setdefault(key, []).append(fact)
    for (metric, period), rows in keyed.items():
        if len(rows) > 1:
            issues.append(issue('duplicate_mapping', rows[0]['statement'], f'Ambiguous mapping: {metric}/{period}'))
    for period in periods:
        for code, account in profile.accounts.items():
            if account.required and (code, period) not in keyed:
                issues.append(issue('missing_row', account.statement, f'Missing configured row: {code}/{period}/{scope}', outcome='skipped'))
        for eq in profile.equations:
            refs = [keyed.get((code, period), []) for code in eq.terms]
            statements = sorted({profile.accounts[code].statement for code in eq.terms})
            name = f'{eq.id}/{period}/{scope}'
            if any(len(rows) != 1 for rows in refs):
                if eq.required:
                    issues.append(issue(name, statements, 'Equation skipped: missing or ambiguous operands', outcome='skipped'))
                checks.append(dict(check=name, outcome='skipped', required=eq.required))
                continue
            operands = [rows[0] for rows in refs]
            if len({f['currency'] for f in operands}) != 1:
                issues.append(issue(name, statements, 'Mixed currencies cannot be reconciled without sourced FX'))
                continue
            residual = sum((Decimal(f['value']) * eq.terms[f['metric']] for f in operands), Decimal(0))
            # Tolerance is configured in reported units; scale to currency units.
            tolerance = Decimal(eq.tolerance) * min(Decimal(f['scale']) for f in operands)
            outcome = 'passed' if abs(residual) <= tolerance else 'failed'
            checks.append(dict(check=name, outcome=outcome, residual=str(residual), tolerance=str(tolerance),
                operands={f['metric']: f['value'] for f in operands},
                evidence_ids=sorted({e for f in operands for e in f['evidence_ids']})))
            if outcome == 'passed':
                passed.append(name)
            else:
                issues.append(issue(name, statements, f'Arithmetic does not reconcile: residual {residual}',
                    residual=str(residual), tolerance=str(tolerance)))
    status = 'invalid' if any(i['outcome'] == 'failed' for i in issues) else 'manual review' if issues else 'valid'
    if not facts:
        status = 'invalid'
    # Ambiguous duplicate cells are never published as usable values.
    facts = [f for f in facts if len(keyed[(f['metric'], f['period'])]) == 1]
    return dict(status=status, issues=issues, checks=checks, checks_passed=passed, facts=facts)
