"""Supported semantic adapters over immutable draft claims and Python tables.

Unknown fields stay named gaps. No extraction, numeric inference or provider calls.
"""
from decimal import Decimal
import re

from ..services.templates import W, paragraph_text
from .presentation import Presentation
from .formatting import number, prose, human_date
from .word import cells, rows, fill_row, repeat_rows, facility_columns, set_cell, set_paragraph

VERSION = 'template-export-v3'


class Mapper(Presentation):
    def __init__(self, copy, manifest):
        self.copy, self.manifest = copy, manifest
        self.consumed = set()
        self.gaps = manifest['mapping_gaps']
        self.source_numbers = {key: i for i, key in enumerate(manifest['sources'], 1)}
        manifest['source_markers'] = {str(i): key for key, i in self.source_numbers.items()}
        self.seen_claims = {}
        self.fills = manifest['filled_targets'] = {}

    def gap(self, table, cell):
        anchor = cell['key']
        self.gaps.append(dict(anchor=anchor, section_id=table['section_id'],
            field=f"{cell['row_label']} / {cell['column_header']}", reason='Supported field mapping/value not supplied'))
        return '[Gap]'

    def table(self, key):
        return self.copy.bound.get(key)

    def put(self, key, ri, ci, text):
        if self.table(key) is None:
            return
        set_cell(cells(rows(self.table(key))[ri])[ci], text)
        self.fills[f'{key}.r{ri}.c{ci}'] = text
        self.gaps[:] = [g for g in self.gaps if g.get('anchor') != f'{key}.r{ri}.c{ci}']

    def record_rows(self, key, values, *, total=False, start=1):
        table = self.table(key)
        if table is None:
            return
        if values:
            percent_columns = {'s4.portfolio': {5}, 's5.holders': {1}, 's8.security': {5}, 's9.tenants': {2}, 's9.lease_profile': {1, 2}}
            values = [[re.sub(r'^(-?\d+(?:\.\d+)?)(?=\s|$)', lambda m: number(m[1], 'percent'), str(v))
                       if ci in percent_columns.get(key, set()) else v for ci, v in enumerate(row)] for row in values]
            repeat_rows(table, values, start=start, total=total)
            self.fills[key] = dict(repeat='rows', start=start, total_retained=total, records=values)
            end = len(next(t for t in self.copy.report['tables'] if t.get('anchor')==key)['rows']) - int(total)
            prefixes = tuple(f'{key}.r{i}.' for i in range(start, end))
            self.gaps[:] = [g for g in self.gaps if not g.get('anchor', '').startswith(prefixes)]
        else:
            # A single explicit gap row, never a sample entity or an inferred nil.
            repeat_rows(table, [['[GAP]'] * len(cells(rows(table)[start]))],
                        start=start, total=total)

    def refs(self, refs):
        return ' '.join(f'[{self.source_numbers[ref]}]' for ref in dict.fromkeys(refs))

    def appendix(self):
        entries = []
        for ref, i in self.source_numbers.items():
            src = self.manifest['sources'][ref]
            if src['origin'] == 'CA input':
                detail = (f"CA input; Credit Analyst; {human_date(src['recorded_at'])}; "
                          f"revision {src['revision']}; not independently verified")
                if src['synthetic']: detail += '; SYNTHETIC'
            else:
                label = 'SYNTHETIC' if src['synthetic'] else 'Public' if src['origin'] == 'public' else 'Supplied'
                detail = f"{src['filename']} p{src['page']}; {label}; revision {src['revision']}"
                if src['origin'] == 'public':
                    detail += '; CA confirmed' if src['confirmed_by'] else '; CA confirmation pending'
                    detail += f"; {src['url']}; retrieved {human_date(src['retrieved_at'])}"
                if not src['current_at_export']: detail += '; superseded source retained in saved draft'
            entries.append(f'[{i}] {detail}')
        self.copy.appendix('Sources', entries or ['No sources: no supported draft supplied.'])

    def claim(self, claim, *, facility_label=True):
        text = claim['text']
        if not any(claim.get(k) for k in ('ca_edit', 'ca_input', 'ca_position')):
            text = prose(text)
        if facility_label and claim.get('kind') == 'facility':
            text = f"{claim['facility']} / {claim['field']}: {text}"
        text += ' ' + self.refs(claim.get('evidence_ids', []))
        if claim.get('ca_edit'):
            edit = claim['ca_edit']
            text += f" CA-edited wording: CA (Credit Analyst), {human_date(edit['recorded_at'])}; not independently verified."
        if claim.get('ca_confirmation'):
            text += ' CA confirmation: Credit Analyst; supplied description only.'
        if claim.get('ca_position'):
            pos = claim['ca_position']
            text += f" CA input: Credit Analyst, {human_date(pos['recorded_at'])}; not independently verified."
        if claim.get('kind') == 'case_input':
            text += ' Explicit case input: new_to_bank=true.'
        return text.strip()

    def consume_table(self, table, metrics=None):
        self.consumed.update(c['computed_value_id'] for c in table['cells'] if c.get('value') is not None
                             and (metrics is None or c['metric'].rsplit('/', 1)[-1] in metrics))

    def computation_tables(self, sid, draft):
        for table in draft['claim_spans'][0].get('computed_tables', []):
            kind = table['kind']
            refs = self.refs([x['evidence_id'] for x in table['source_register']])
            if kind=='exposure' and sid==2 and self.table('s2.exposure') is not None:
                values = []
                # Columns added by a newer template (for example the limit cap) have no sourced value yet.
                extra = ['[GAP: not supplied]'] * (len(cells(rows(self.table('s2.exposure'))[0])) - 8)
                for r in table['rows']:
                    # Exposure header's default SGD'000 is explicitly replaced by SGD million.
                    values.append([r['entity'], r['facility'], *[number(r[k]) for k in ('existing','outstanding','proposed','increase')],
                                   r['existing_maturity'], '[GAP: confirm basis]', *extra])
                self.record_rows('s2.exposure', values, total=True)
                if table.get('totals'):
                    fill_row(rows(self.table('s2.exposure'))[-1], ['Total obligor group',
                        *[number(table['totals'][k]) for k in ('existing','outstanding','proposed','increase')], 'See details', 'See section 8', *extra])
                    self.gaps[:] = [g for g in self.gaps if not g.get('anchor','').startswith('s2.exposure.')]
                    self.gaps.append(dict(section_id=2,anchor='s2.exposure.security',reason='Security classification requires explicit CA confirmation; see section 8.'))
                self.consume_table(table, {'existing','outstanding','proposed','increase'})
                yield 'Exposure: SGD million; as at ' + ', '.join(sorted({r['period'] for r in table['rows']})) + '; existing maturity shown. ' + refs
            elif kind=='conduct' and sid==13 and self.table('s13.conduct') is not None:
                values=[]
                for r in table['rows']:
                    values.append([r['facility'],number(r['limit']),number(r['peak']),number(r['mean_month_end']),
                        ' / '.join(number(r[k], 'currency_million' if k=='max_excess' else 'count') for k in ('excess_count','max_excess','excess_days')),
                        ' / '.join(number(r[k], 'count') for k in ('past_due_count','max_dpd')),
                        f"{r['period_start']} to {r['period_end']}; SGD million. Mean of 12 month ends, not daily. Exceptions require CA review."])
                self.record_rows('s13.conduct',values)
                self.consume_table(table, {'limit','peak','mean_month_end','excess_count','max_excess','excess_days','past_due_count','max_dpd'})
            elif kind=='covenants' and sid==13 and self.table('s13.compliance') is not None:
                def covenant_unit(row):
                    return next(c['unit'] for c in table['cells'] if c['metric']=='covenant/'+row['covenant'])
                self.record_rows('s13.compliance', [[r['covenant'],r['direction']+' '+number(r['limit'], covenant_unit(r)),r['test_date'],number(r['actual'], covenant_unit(r)),r['status']] for r in table['rows']])
                self.consume_table(table)
            elif kind=='projections' and sid==9 and self.table('s9.debt_service') is not None:
                # Historical slots remain gaps. Put every forecast year in the existing
                # projected column, explicitly labelled; no invented period columns.
                self.put('s9.debt_service',0,3,'Projected years')
                for ri,key in [(1,'npi'),(2,'interest'),(4,'dscr')]:
                    self.put('s9.debt_service',ri,3,'\n'.join(f"{r['year']}: " + ('n.m.' if key=='dscr' and Decimal(r['principal']) > 0 else number(r[key])) for r in table['rows']))
                    self.put('s9.debt_service',ri,4,('n.m.: cash repayment of bullet maturities; no refinancing receipt assumed.' if key=='dscr' else 'Property scenario; SGD million.') + ' ' + refs)
                    self.consumed.update(c['computed_value_id'] for c in table['cells'] if c['metric'].rsplit('/',1)[-1]==key)
                yield 'Projection sources: ' + refs

    def facilities(self, claims):
        table=self.table('s7.facilities')
        if table is None:
            return
        mapping={'Currency and amount':'Proposed limit','Tenor / final maturity':'Maturity / repayment',
                 'Repayment':'Maturity / repayment','Pricing (margin / fees)':'Pricing','Security':'Security',
                 **{k:k for k in ('Borrower','Facility type','Purpose','Availability period','Financial covenants','Other key terms and conditions')}}
        grouped={}
        for claim in claims:
            if claim.get('kind')=='facility':
                grouped.setdefault(claim['facility'],{}).setdefault(claim['field'],[]).append(claim)
        columns=[]
        for name, fields in grouped.items():
            column=[name]
            for row in rows(table)[1:]:
                label=paragraph_text(cells(row)[0])
                found=fields.get(mapping.get(label),[])
                column.append('\n'.join(self.claim(c, facility_label=False) for c in found) if found else '[GAP: '+label+']')
            columns.append(column)
        if not columns:
            columns=[['[GAP: facility]']+['[GAP]']*(len(rows(table))-1)]
        try:
            facility_columns(table,columns)
            self.fills['s7.facilities'] = dict(repeat='facility_columns', columns=columns)
        except ValueError as error:
            self.gaps.append(dict(section_id=7,anchor='s7.facilities',reason=str(error)))
            return  # Complete claims still appear in the narrative slot, no truncation.
        for fields in grouped.values():
            self.consumed.update(c['id'] for name,claims in fields.items() if name in mapping.values() for c in claims)
        self.gaps[:] = [g for g in self.gaps if not g.get('anchor','').startswith('s7.facilities.r')]
        for name,fields in grouped.items():
            for row in rows(table)[1:]:
                label=paragraph_text(cells(row)[0])
                if not fields.get(mapping.get(label)):
                    self.gaps.append(dict(section_id=7,anchor=f's7.facilities.{name}.{label}',reason='Supported field not supplied'))
        if not grouped:
            self.gaps.append(dict(section_id=7,anchor='s7.facilities',reason='Facility records not supplied'))

    def financials(self, claims):
        mapping={'aggregate_leverage':'Aggregate leverage (%)','interest_coverage':'Interest coverage (x)',
                 'average_cost_of_debt':'Average cost of debt (%)',
                 'weighted_debt_maturity':'Weighted average debt maturity (years)',
                 'fixed_rate_share':'Fixed rate debt (%)','occupancy':'Occupancy (%)','wale':'WALE (years)'}
        metrics={}
        for claim in claims:
            v=claim.get('value',{})
            if v.get('metric') in mapping:
                metrics.setdefault(v['metric'],[]).append(claim)
        for metric, candidates in metrics.items():
            if len(candidates)!=1 or self.table('s10.financials') is None:
                continue
            claim=candidates[0]; v=claim['value']
            matches=[i for i,row in enumerate(rows(self.table('s10.financials'))) if paragraph_text(cells(row)[0])==mapping[metric]]
            if len(matches)!=1:
                continue
            ri=matches[0]
            ci = self.period_columns.get(v['period'][:4])
            if ci is None: continue
            self.put('s10.financials',ri,ci,number(v['value'],v['unit']))
            self.put('s10.financials',ri,5,('PROXY; ' if v['proxy'] else '')+self.refs(claim['evidence_ids']))
            self.consumed.add(claim['id'])
            if metric == 'interest_coverage':
                self.put('s10.sensitivity',1,1,number(v['value'])+'; '+v['period']+' '+self.refs(claim['evidence_ids']))
            # Thresholds were computed and persisted by B10, not inferred here.
            thresholds=[t for t in claim.get('thresholds',[]) if t.get('headroom') is not None]
            if metric in {'aggregate_leverage','interest_coverage'} and thresholds and self.table('s10.headroom') is not None:
                t=thresholds[0]; hr=1 if metric=='aggregate_leverage' else 2
                self.put('s10.headroom',hr,1,number(t['limit'],v['unit']))
                self.put('s10.headroom',hr,2,number(v['value'],v['unit'])+' '+v['unit'])
                self.put('s10.headroom',hr,3,number(t['headroom'],t['headroom_unit'])+' '+t['headroom_unit'])
                self.put('s10.headroom',hr,4,t['status']+'; '+v['period']+' '+self.refs(claim['evidence_ids']))

    def spread_financials(self, claims):
        # B09 reports base currency. Only exact supported metrics/units/scopes
        # enter S$m slots; all other validated claims retain their narrative.
        mapping = {'property_income': 'Gross revenue', 'npi': 'Net property income', 'total_assets': 'Total assets'}
        key = 's10.financials'
        table = self.table(key)
        if table is None:
            return
        candidates = [c for c in claims if c.get('value', {}).get('metric') in mapping
                      and c['value']['unit'] == 'currency' and c['value']['currency'] == 'SGD'
                      and c['value']['scope'] == 'Group' and not c['value']['proxy']]
        periods = sorted({c['value']['period'] for c in candidates})
        if len(periods) > 2:
            self.gaps.append(dict(section_id=10, anchor=key, reason='More than two comparable spread periods; values retained in narrative'))
            return
        for period in periods:
            ci = self.period_columns.get(period[:4])
            if ci is None: continue
            self.put(key, 0, ci, 'FY' + period)
            for metric, label in mapping.items():
                found = [c for c in candidates if c['value']['metric'] == metric and c['value']['period'] == period]
                matches = [i for i, row in enumerate(rows(table)) if paragraph_text(cells(row)[0]) == label]
                if len(found) != 1 or len(matches) != 1:
                    continue
                claim = found[0]; ri = matches[0]
                amount = Decimal(claim['value']['value']) / Decimal(1000000)
                self.put(key, ri, ci, self.money(amount))
                # Both periods' sources survive in the remarks cell.
                old = self.fills.get(f'{key}.r{ri}.c5', '')
                self.put(key, ri, 5, ' '.join(dict.fromkeys((old + ' ' + self.refs(claim['evidence_ids'])).split())))
                self.consumed.add(claim['id'])

    def rating(self, claims):
        # Decode the existing reviewed, protected supplied-rating claim only.
        # A different/edited phrasing remains a named field gap, not a guess.
        for claim in claims:
            if not claim.get('internal_rating') or claim.get('ca_edit'):
                continue
            match = re.match(r'The supplied internal rating is ([^,]+), provided by (.+?) on (.+?)\. The report records the previous grade as (.+?) dated (.+?)\.', claim['text'])
            if match:
                self.record_rows('s12.internal_rating', [[self.manifest['borrower_name'] + ' (case input)',
                    match[1], match[4], match[3], self.claim(claim)]])
                self.consumed.add(claim['id'])

    def covenant_headroom(self):
        section = self.manifest['sections'].get('13', {})
        draft = section.get('draft')
        if not draft or self.table('s10.headroom') is None:
            return
        for table in draft['claim_spans'][0].get('computed_tables', []):
            if table['kind'] != 'covenants':
                continue
            refs = self.refs([s['evidence_id'] for s in table['source_register']])
            units = {r['covenant']: next(c['unit'] for c in table['cells'] if c['metric'] == 'covenant/' + r['covenant']) for r in table['rows']}
            values = [[r['covenant'], r['direction'] + ' ' + number(r['limit'], units[r['covenant']]), number(r['actual'], units[r['covenant']]),
                       number(r['headroom'], units[r['covenant']]) + ' ' + units[r['covenant']],
                       r['status'] + '; ' + r['test_date'] + '. ' + refs]
                      for r in table['rows']]
            self.record_rows('s10.headroom', values, start=3)

    def run(self):
        self.copy.sanitize(self.gap)
        # These are fixed business labels, not the sample records elsewhere.
        for table in self.copy.report['tables']:
            key = table.get('anchor', '')
            for row in table['rows']:
                if not row:
                    continue
                first = row[0]
                if (first['text'].startswith('Total') or
                        key == 's1.classification' and first['row'] >= 2 or
                        key == 's14.signoff' and first['row'] > 0):
                    self.put(key, first['row'], 0, first['text'])
        for fill in self.copy.report['fill_points']:
            if fill['kind'] == 'period':
                self.gaps.append(dict(section_id=fill['section_id'], anchor=fill['id'],
                    reason='Reporting period not mapped; see explicitly labelled values where supplied'))
        cover='s0.cover'
        self.put(cover,0,1,self.manifest['borrower_name']+' (case input)')
        labels = {section['draft']['claim_spans'][0].get('label', '') for section in self.manifest['sections'].values() if section.get('draft')}
        mode = 'Mock text' if labels and all('MOCK' in label for label in labels) else 'Mixed mock/live text' if any('MOCK' in label for label in labels) else 'Live / CA text' if labels else 'No drafted text'
        status = 'DRAFT — CA REVIEW REQUIRED; template ' + self.manifest['template']['display_version'] + '; ' + mode
        status += '; SYNTHETIC DEMO DATA included' if any(s['synthetic'] for s in self.manifest['sources'].values()) else '; no synthetic sources included'
        if any(s['readiness']=='Stale' for s in self.manifest['sections'].values()): status += '; STALE DRAFT — changed inputs require review'
        self.copy.status(status)
        self.put(cover,0,2,'Paper type / watchlists: [GAP: explicit input required]')
        for sid,section in self.manifest['sections'].items():
            sid=int(sid); draft=section.get('draft')
            fills=[f for f in self.copy.report['fill_points'] if f['section_id']==sid and f['kind']=='placeholder'
                   and f['mapped'] and f['table_id']==self.copy.report['bindings'].get(f's{sid}.wrapper')]
            paragraphs=[]
            if not section['applicable']:
                paragraphs += ['Not applicable: '+section['na_reason']]
            elif not draft:
                paragraphs += [f'[GAP] Section {sid}: draft not supplied.']
            else:
                claims=draft['claim_spans'][1:]
                if sid == 10: self.financial_period_columns(claims)
                self.field_claims(sid, claims)
                if sid == 1: self.request_justification(claims)
                paragraphs += list(self.computation_tables(sid,draft))
                if sid==7: self.facilities(claims)
                if sid==9: self.historical_repayment(claims)
                if sid==10:
                    self.financials(claims)
                    self.spread_financials(claims)
                    self.reviewed_financials(claims)
                    paragraphs += self.financial_commentary(claims)
                if sid==13: paragraphs += self.conduct_summary(draft)
                if sid==12: self.rating(claims)
                for claim in claims:
                    if claim.get('dependency_draft_id') or (sid == 9 and claim.get('value', {}).get('metric', '').startswith('projection/')):
                        continue
                    signature=(claim['text'],tuple(claim.get('evidence_ids',[])))
                    if claim['id'] in self.consumed or claim.get('computed_value_id') in self.consumed:
                        self.seen_claims.setdefault(signature,sid)
                        continue
                    if claim.get('dependency_draft_id') and signature in self.seen_claims:
                        continue  # Explicit cross-reference below; exact draft remains in manifest.
                    paragraphs.append(self.claim(claim)); self.seen_claims.setdefault(signature,sid)
                dependencies=draft['claim_spans'][0].get('dependencies',{})
                if dependencies and sid != 9:
                    paragraphs.append('Read with sections '+', '.join(dependencies)+'.')
                own_gaps=[g for g in draft['gaps'] if not any(g.startswith('Section '+n+': ') for n in dependencies)]
                paragraphs += list(dict.fromkeys(self.short_gap(g) for g in self.visible_gaps(sid, own_gaps)))
            if sid == 9 and draft and fills:
                self.repayment(draft, fills, paragraphs)
            elif sid == 11:
                self.risk_rows(draft['claim_spans'][1:] if draft else [])
            elif sid == 4 and self.table('s4.overview') is not None:
                # Newer templates hold the business overview in its own box, not in the wrapper.
                self.put('s4.overview', 1, 0, '\n'.join(paragraphs))
                for fill in fills:
                    self.copy.narrative(fill['id'], [''])
            elif fills:
                # Place prose after the table where the template provides a
                # commentary slot, and under Requests rather than above it.
                target = fills[-1] if sid in (1, 10) else fills[0]
                for fill in fills:
                    self.copy.narrative(fill['id'], paragraphs if fill == target else [''])
                self.fills[target['id']] = dict(paragraphs=paragraphs)
            else:
                self.gaps.append(dict(section_id=sid,anchor=f's{sid}.narrative',reason='No unambiguous text slot; section content retained in metadata'))
        # Remove factual-looking fixed date guidance and leave all decision boxes
        # unselected. These are template instructions, not human workflow events.
        for sid in (1,8,14):
            wrapper=self.table(f's{sid}.wrapper')
            if wrapper is not None:
                for paragraph in wrapper.findall(W+'tr/'+W+'tc/'+W+'p'):
                    text=paragraph_text(paragraph)
                    if text.startswith('CAS Approved on'):
                        set_paragraph(paragraph,'[Gap: prior CAS approval date]')
                    elif 'Pending CA selection' in text and sid != 1:
                        set_paragraph(paragraph,'[Gap: CA selection]')
        # Collapse unused record seeds, preserving fixed total and regulatory rows.
        for t in self.copy.report['tables']:
            key=t.get('anchor')
            if key and t.get('repeat')=='rows' and key not in self.fills and key not in {'s2.exposure','s13.conduct','s13.compliance','s11.risks','s12.internal_rating'}:
                self.record_rows(key,[],total=any(r and r[0]['text'].startswith('Total') for r in t['rows']))
        self.classification()
        self.covenant_headroom()
        self.appendix()
        return self.copy.bytes()
