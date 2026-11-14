"""Bounded presentation adapters for validated saved claims, never raw evidence.

A changed/CA-edited claim is kept verbatim in narrative instead of decoded using
an obsolete field schema. Numbers below are captures of Python-validated claims.
"""
import re
from decimal import Decimal, ROUND_HALF_UP
from .formatting import number

from .word import cells, rows, fill_row


class Presentation:
    def saved(self, claims, key, pattern):
        candidates = [c for c in claims if (c['id'] == key or key in c.get('origin_claim_ids', []))
                      and not c.get('ca_edit') and not c.get('ca_input')]
        if len(candidates) != 1:
            return None
        c = candidates[0]
        match = re.fullmatch(pattern, c['text'])
        return (c, match) if match else None

    def field_claims(self, sid, claims):
        def match(key, pattern):
            return self.saved(claims, key, pattern)

        def put(key, ri, ci, value, claim):
            self.put(key, ri, ci, value + ' ' + self.refs(claim['evidence_ids']))

        if sid == 3:
            updates = []
            for key in ('disposal', 'rent-update'):
                c = next((c for c in claims if c['id'] == key), None)
                if c:
                    src = self.manifest['sources'][c['evidence_ids'][0]]
                    updates.append((c['id'], [src['period'], c['text'], self.refs(c['evidence_ids']), 'Review required', '']))
            # Templates without a developments table keep these updates in the section narrative.
            if updates and self.table('s3.developments') is not None:
                self.record_rows('s3.developments', [row for _, row in updates])
                self.consumed.update(key for key, _ in updates)
            c = next((c for c in claims if c['id'] == 'conditions'), None)
            if c:
                self.record_rows('s3.prior_conditions', [['1', c['text'], 'Acceptance outstanding', self.refs(c['evidence_ids'])]])
                self.consumed.add(c['id'])
        if sid == 4:
            for key, text, row, value in [('country', 'ESR-REIT is constituted in Singapore.', 2, 'Singapore'),
                    ('obligor-group', 'ESR Group is the sponsor group of ESR-REIT.', 1, 'ESR Group')]:
                hit = match(key, re.escape(text))
                if hit:
                    put('s0.cover', row, 1, value, hit[0]); self.consumed.add(key)
            hit = match('business', r'(.+?) is a Singapore-listed real estate investment trust investing in (.+?)\. (.+)')
            if hit:
                c, m = hit
                put('s4.business', 0, 1, m[1], c)
                put('s4.business', 4, 1, 'Investing in ' + m[2] + '.', c)
            hit = match('listing', r'.+? has been listed on the (.+?) since (.+?)\. Its website is (.+)\.')
            if hit:
                c, m = hit
                for ri, value in [(1, m[2]), (2, m[1]), (7, m[3])]: put('s4.business', ri, 1, value, c)
                self.consumed.add(c['id'])
            hit = match('sponsor', r'The REIT is managed by (.+?) and sponsored by (.+?), as described in the FY2025 report\.')
            if hit:
                c, m = hit; put('s4.business', 5, 1, 'Manager: ' + m[1] + '; sponsor: ' + m[2], c)
                self.consumed.add(c['id'])
            hit = match('trustee-4', r'The FY2025 annual report identifies (.+?) as trustee of (.+)\.')
            if hit:
                c, m = hit; put('s4.business', 6, 1, m[1], c); self.consumed.add(c['id'])
            hit = match('portfolio', r'At (.+?), portfolio valuation was SGD ([\d.]+) million and occupancy was ([\d.]+)%\. The portfolio spans (.+)\.')
            wale = match('portfolio-wale-4', r'At (.+?), portfolio WALE by gross rental income was ([\d.]+) years\. (.+)')
            if hit:
                c, m = hit
                self.record_rows('s4.portfolio', [['Portfolio summary', m[4], 'Industrial properties', number(m[2]), m[1], m[3],
                    wale[1][2] + ' (by rent)' if wale else '[Gap: WALE]']], total=True)
                table = self.table('s4.portfolio')
                if table is not None:
                    self.record_total('s4.portfolio', ['Total portfolio ' + self.refs(c['evidence_ids']), number(m[2]), m[1], number(m[3], 'percent'),
                                              wale[1][2] + ' ' + self.refs(wale[0]['evidence_ids']) if wale else '[Gap: WALE]'])
                self.consumed.add(c['id'])
                if wale: self.consumed.add(wale[0]['id'])
        if sid == 5:
            hit = match('unitholders', r'The substantial-unitholder register at (.+?) reports (.+?) with a total deemed interest of ([\d.]+)% and (.+?) with a total interest of ([\d.]+)%\. (.+)')
            if hit:
                c, m = hit; ref = self.refs(c['evidence_ids'])
                self.record_rows('s5.holders', [[m[2], m[3], 'Deemed interest; ' + m[1] + '. ' + ref],
                    [m[4], m[5], 'Total interest; ' + m[1] + '. ' + ref]], total=True)
                table = self.table('s5.holders')
                if table is not None: self.record_total('s5.holders', ['Total', 'Not additive', 'Overlapping deemed interests; public/others not reconciled. ' + ref])
                self.consumed.add(c['id'])
            for c in claims:
                if c['id'] == 'trust-structure':
                    self.put('s5.structure_chart', 0, 0, self.claim(c)); self.consumed.add(c['id'])
        if sid == 6:
            hit = match('management', r'The FY2025 management team disclosure names (.+)\.')
            if hit:
                c, m = hit
                entries = re.findall(r'(?:^|, and |, )([^,]+?) as ([^,]+)', m[1])
                if entries:
                    values = [[name, role, '[Gap: experience / tenure]', 'FY2025 ' + self.refs(c['evidence_ids'])] for name, role in entries]
                    tenure = match('management-tenure', r'(.+?) joined the manager as CEO and Executive Director in (.+?); (.+?) was appointed CFO on (.+?)\. (.+)')
                    if tenure:
                        tc, tm = tenure
                        for row in values:
                            if row[0] == tm[1]: row[2] = 'Joined ' + tm[2] + ' ' + self.refs(tc['evidence_ids'])
                            if row[0] == tm[3]: row[2] = 'Appointed ' + tm[4] + ' ' + self.refs(tc['evidence_ids'])
                    self.record_rows('s6.management', values); self.consumed.add(c['id'])
            values = []
            hit = match('stakeholders', r'(.+?) is the sponsor and (.+?) is the manager\. (.+)')
            if hit:
                c, m = hit
                values.extend([[m[1], 'Sponsor', m[3] + ' ' + self.refs(c['evidence_ids'])],
                               [m[2], 'Manager', 'REIT management. ' + self.refs(c['evidence_ids'])]])
                self.consumed.add(c['id'])
            hit = match('trustee-6', r'The FY2025 annual report identifies (.+?) as trustee of (.+)\.')
            if hit:
                c, m = hit; values.append([m[1], 'Trustee', 'Trustee of ' + m[2] + '. ' + self.refs(c['evidence_ids'])]); self.consumed.add(c['id'])
            if values: self.record_rows('s6.stakeholders', values)
        if sid == 8:
            hit = match('insurance', r'(.+?) provides (.+?) cover for (.+?) from (.+?) to (.+?)\. Reinstatement sum insured is SGD ([\d.]+) million; the Bank is named as (.+?)\. (.+)')
            if hit:
                c, m = hit
                for ri, value in enumerate([m[1], 'SGD ' + m[6] + ' million (reinstatement)', m[2], m[5], m[7]]):
                    put('s8.insurance', ri, 1, value, c)
                # Retain exclusions/adequacy qualifications in the narrative.
            valuation = match('valuation-revised', r'(.+?) reports a revised market value of SGD ([\d.]+) million for (.+?), effective (.+?), following (.+)') or match('valuation', r'(.+?) reports a market value of SGD ([\d.]+) million for (.+?), effective (.+?); basis: (.+)')
            ltv = match('security-ltv-revised', r'Fully drawn TL of SGD ([\d.]+) million against market value of SGD ([\d.]+) million gives ([\d.]+)% LTV, with ([-\d.]+) percentage points of headroom to the ([\d.]+)% contractual maximum\. (.+)') or match('security-ltv-initial', r'Fully drawn TL of SGD ([\d.]+) million against market value of SGD ([\d.]+) million gives ([\d.]+)% LTV, with ([-\d.]+) percentage points of headroom to the ([\d.]+)% contractual maximum\. (.+)')
            security = next((c for c in claims if c['id'] == 'tl-security-8' and not c.get('ca_edit')), None)
            if security:
                ref = self.refs(security['evidence_ids'])
                self.record_rows('s8.security', [['Proposed first mortgage and rent assignment',
                    valuation[1][3] if valuation else security['text'], valuation[1][2] if valuation else '[Gap: valuation]',
                    valuation[1][1] + '; ' + valuation[1][4] + ' ' + self.refs(valuation[0]['evidence_ids']) if valuation else '[Gap: valuer/date]',
                    'Market value' if valuation else '[Gap: basis]', ltv[1][3] + ' ' + self.refs(ltv[0]['evidence_ids']) if ltv else '[Gap: LTV]',
                    'Legal perfection requires evidence; no corporate guarantee assumed. ' + ref]])
        if sid == 9:
            hit = match('top-tenants', r'At (.+?), (.+?) \((.+?)\) accounts for ([\d.]+)% of contractual annual rent, expiring (.+?); (.+?) \((.+?)\), ([\d.]+)%, expires (.+?); (.+?) \((.+?)\), ([\d.]+)%, expires (.+?)\. (.+)')
            if hit:
                c, m = hit; ref = self.refs(c['evidence_ids'])
                self.record_rows('s9.tenants', [[m[i] + ' ' + ref, m[i+1], m[i+2], m[i+3]] for i in (2, 6, 10)])
                self.consumed.add(c['id'])
            hit = match('lease-expiries', r'The property lease schedule at (.+?) shows ([\d.]+)% of rent expiring in (\d{4}), ([\d.]+)% in (\d{4}) and ([\d.]+)% in (\d{4})\. The corresponding shares of total net lettable area are ([\d.]+)%, ([\d.]+)% and ([\d.]+)%; vacant space is ([\d.]+)% of total area\. (.+)')
            if hit:
                c, m = hit; ref = self.refs(c['evidence_ids'])
                self.record_rows('s9.lease_profile', [[m[3] + ' ' + ref, m[2], m[8]], [m[5] + ' ' + ref, m[4], m[9]],
                    [m[7] + ' ' + ref, m[6], m[10]], ['Vacant ' + ref, 'No rent', m[11]]])
                self.consumed.add(c['id'])
        if sid == 10:
            hit = match('portfolio-wale-10', r'At (.+?), portfolio WALE by gross rental income was ([\d.]+) years\. (.+)')
            if hit and hit[1][1][-4:] in self.period_columns:
                c, m = hit; put('s10.financials', 20, self.period_columns[m[1][-4:]], m[2], c)
                self.put('s10.financials', 20, 5, self.refs(c['evidence_ids'])); self.consumed.add(c['id'])
            hit = match('occupancy-commentary', r'Portfolio occupancy declined from ([\d.]+)% at 31 December (\d{4}) to ([\d.]+)% at 31 December (\d{4})\. (.+)')
            if hit and all(hit[1][i] in self.period_columns for i in (2, 4)):
                c, m = hit
                for ci, val in [(self.period_columns[m[2]], m[1]), (self.period_columns[m[4]], m[3])]: put('s10.financials', 19, ci, val, c)
                self.put('s10.financials', 19, 5, self.refs(c['evidence_ids']))
        if sid == 12:
            hit = match('external-rating', r'(.+?) published .+?\'s long-term IDR at (.+?) with (.+?) outlook on (.+?)\. (.+)')
            if hit:
                c, m = hit
                self.record_rows('s12.external_ratings', [[m[1], m[2] + ' (long-term IDR)', m[3], m[4] + ' ' + self.refs(c['evidence_ids'])]])
                self.consumed.add(c['id'])

    def risk_rows(self, claims):
        values = []
        for c in claims:
            if c.get('kind') != 'risk_mitigant' and c['id'] != 'lease-risk': continue
            title, sep, description = self.claim(c).partition(':')
            if ':' not in c['text']: title, description = 'CA risk assessment', self.claim(c)
            action = '[Gap: mitigant evidence]'
            for marker in ('Mitigant review:', 'Potential mitigant:', 'Reassess '):
                if marker in description:
                    description, action = description.split(marker, 1)
                    action = ('Reassess ' if marker == 'Reassess ' else '') + action
                    break
            ref = self.refs(c['evidence_ids'])
            values.append([str(len(values)+1), title, description.strip() + ' ' + ref, action.strip() if ref in action else action.strip() + ' ' + ref])
        # These sourced, already-computed findings provide the actual covenant
        # pressure and concentration, not a model-generated rating or decision.
        for keys, title, action in [
            (('security-ltv-revised', 'security-ltv-initial'), 'LTV covenant headroom', 'Reassess drawings against the latest valuation; obtain legal perfection evidence.'),
            (('top-tenants',), 'Tenant concentration', 'Obtain evidence of renewal or reletting before relying on rental continuity.')]:
            c = next((c for key in keys for c in claims if key in c.get('origin_claim_ids', []) and not c.get('ca_edit')), None)
            if c: values.append([str(len(values)+1), title, self.claim(c), action + ' ' + self.refs(c['evidence_ids'])])
        c = next((c for c in claims if c.get('value', {}).get('metric') == 'aggregate_leverage/headroom/0'), None)
        if c:
            values.append([str(len(values)+1), 'Regulatory leverage headroom', self.claim(c),
                           'Monitor leverage before further borrowing; headroom is not a committed funding source. ' + self.refs(c['evidence_ids'])])
        self.record_rows('s11.risks', values)

    @staticmethod
    def short_gap(gap):
        # Keep the input/field name; readiness/search mechanics live in the app.
        if gap.startswith(('Industry code:', 'Industry code mapping:')):
            return '[Gap: CA-confirmed industry code; property WALE not provided]'
        if any(status in gap for status in ('Found publicly', 'Can generate', 'Missing', 'Suggested', 'reviewed supporting detail remains outstanding')):
            name = gap.split(':', 1)[0]
            return '[Gap: ' + name + ' evidence incomplete]'
        concise = {
            'Classification table': 'CA classification and Watchlist/SM assessment not provided',
            'Income / balance sheet': 'Unfilled financial rows and matched stress inputs not validated',
            'Debt service capacity': 'Group forecast and committed maturity funding not provided',
            'Conditions and covenants': 'CA-adopted conditions and timing pending; sign-off pending',
            'Security': 'Title, ranking and perfection evidence outstanding; full insurance policy review pending',
            'External ratings': 'Subsequent agency actions not provided',
            'Financial statements': 'Remaining financial figures require validation',
        }
        topic = gap.split(':', 1)[0]
        if topic in concise: return '[Gap: ' + concise[topic] + ']'
        return '[Gap: ' + gap.replace('Supported field mapping/value not supplied', 'input not provided').rstrip('.') + ']'

    def repayment(self, draft, fills, paragraphs):
        claims = draft['claim_spans'][1:]
        assumptions = self.saved(claims, 'repayment-assumptions',
            r'Primary repayment is assessed against the supplied property cash-flow scenario\. The forecast assumes lease renewals at unchanged rents; these renewals are not committed\. Secondary repayment through refinancing is not committed and no refinancing receipt is assumed\. This property scenario does not establish consolidated group repayment capacity\.')
        if assumptions:
            c, _ = assumptions; ref = self.refs(c['evidence_ids'])
            primary = 'Primary repayment relies on the supplied property cash-flow scenario, which assumes unchanged rents on uncommitted renewals and does not establish consolidated group capacity. ' + ref
            summaries = [c for c in claims if c['kind'] == 'computed_summary' and not c.get('dependency_draft_id')]
            if summaries:
                primary += ' Property-only repayment is insufficient in the forecast years identified in the debt-service table; additional funding requires evidence. ' + self.refs([r for c in summaries for r in c['evidence_ids']])
            secondary = 'Secondary repayment through refinancing is uncommitted; no refinancing receipt is assumed. ' + ref
            handled = {'repayment-assumptions', *self.consumed}
            tenants = self.saved(claims, 'repayment-tenants', r"The fictional property rent roll is a snapshot at 31 October 2026, with vacant space and Demo Tenant A's lease expiring on 30 April 2027\. Renewal and reletting assumptions require review before relying on this rental stream for repayment; the rent roll does not evidence committed future renewals\.")
            if tenants: handled.add('repayment-tenants')
            extras = [self.claim(c) for c in claims if c['id'] not in handled and not c.get('dependency_draft_id')
                      and c['kind'] not in ('computed', 'computed_summary')]
            self.copy.narrative(fills[0]['id'], [primary] + extras)
            self.copy.narrative(fills[1]['id'], [secondary])
            if len(fills) > 2: self.copy.narrative(fills[2]['id'], ['Property lease and tenant shares at 31 October 2026; rent shares use contractual annual rent.'])
        else:
            self.copy.narrative(fills[0]['id'], paragraphs)
            for fill in fills[1:]: self.copy.narrative(fill['id'], ['[Gap: repayment source summary]'])

    def reviewed_financials(self, claims):
        table = self.table('s10.financials')
        if table is None: return
        from .word import paragraph_text
        self.financial_values = {}
        for c in claims:
            spec, value = c.get('financial_cell'), c.get('reviewed_value')
            if not spec or not value or c.get('ca_edit') or c.get('ca_input'): continue
            matched = [i for i, row in enumerate(rows(table)) if paragraph_text(cells(row)[0]) == spec['label']]
            ci = 4 if spec['interim'] else self.period_columns.get(value['period'])
            if len(matched) != 1 or ci is None: continue
            ri = matched[0]; amount = Decimal(value['value'])
            if value['unit'] == 'currency_thousand': amount /= 1000
            shown = (self.money(amount) if value['unit'] in ('currency_thousand', 'currency_million') else
                     number(amount, value['unit']) if value['unit'] != 'cents' else format(amount, '.3f'))
            self.put('s10.financials', ri, ci, shown)
            if ci == 4: self.put('s10.financials', 0, ci, 'YTD / at\n30 Sep 2026')
            old = self.fills.get(f's10.financials.r{ri}.c5', '')
            self.put('s10.financials', ri, 5, ' '.join(dict.fromkeys((old + ' ' + self.refs(c['evidence_ids'])).split())))
            self.financial_values[(spec['label'], value['period'])] = (amount, c)
            self.consumed.add(c['id'])

    def financial_commentary(self, claims):
        values = getattr(self, 'financial_values', {})
        result = []
        def pair(label, first, second, sentence):
            a, b = values.get((label, first)), values.get((label, second))
            if a and b:
                result.append(sentence.format(number(a[0], a[1]['reviewed_value']['unit']), number(b[0], b[1]['reviewed_value']['unit'])) + ' ' + self.refs(a[1]['evidence_ids'] + b[1]['evidence_ids']))
        # These qualitative comparisons are bounded to the reviewed fixture claims;
        # CA edits and unknown claims retain their own wording below.
        pair('Distributable income', '2024', '2025', 'Annual distributable income rose from S${}m to S${}m, supporting distributions to unitholders.')
        pair('Aggregate leverage (%)', '2025', '2026-09-30', 'Leverage increased from {}% at FY2025 to {}% at September 2026, reducing borrowing flexibility.')
        pair('Interest coverage (x)', '2025', '2026-09-30', 'Reported ICR improved from {}x to {}x over that period, although debt maturity and refinancing remain relevant to repayment capacity.')
        occupancy = self.saved(claims, 'occupancy-commentary', r'Portfolio occupancy declined from ([\d.]+)% at 31 December (\d{4}) to ([\d.]+)% at 31 December (\d{4})\. (.+)')
        latest_occupancy = values.get(('Occupancy (%)', '2026-09-30'))
        if occupancy and latest_occupancy:
            c, match = occupancy
            result.append(f'Portfolio occupancy recovered from {number(match[3], "percent")}% at FY2025 to {number(latest_occupancy[0], "percent")}% at September 2026, but remained below {number(match[1], "percent")}% at FY2024, warranting attention to reletting and rental continuity. ' + self.refs(c['evidence_ids'] + latest_occupancy[1]['evidence_ids']))
            self.consumed.add(c['id'])
        elif occupancy:
            result.append(self.claim(occupancy[0])); self.consumed.add(occupancy[0]['id'])
        for c in claims:
            if c.get('ca_edit') or c.get('ca_input'): continue
            v = c.get('value', {})
            if v or c['id'] == 'contractual-headroom': self.consumed.add(c['id'])
        if values:
            refs = self.refs([e for _, c in values.values() for e in c['evidence_ids']])
            result.append('Basis: Group figures; borrowings are total gross debt; investment properties exclude assets held for divestment; comparative per-unit figures reflect the unit consolidation. ' + refs)
        return result

    def conduct_summary(self, draft):
        tables = draft['claim_spans'][0].get('computed_tables', [])
        result = []
        for table in tables:
            refs = self.refs([r['evidence_id'] for r in table['source_register']])
            if table['kind'] == 'conduct' and table['rows']:
                exceptions = [r for r in table['rows'] if Decimal(r['excess_count']) or Decimal(r['past_due_count'])]
                events = []
                for r in exceptions:
                    if Decimal(r['excess_count']): events.append(f"{r['facility']} recorded {number(r['excess_count'], 'count')} excess event(s) over {number(r['excess_days'], 'days')} days")
                    if Decimal(r['past_due_count']): events.append(f"{r['facility']} recorded {number(r['past_due_count'], 'count')} past-due event(s), with a maximum delay of {number(r['max_dpd'], 'days')} days")
                result.append(('; '.join(events) + '; these exceptions require CA review.' if events else 'The supplied event register records no excess or past-due events.') + ' ' + refs)
                result.append('Average utilisation is based on twelve month-end balances, so it does not describe daily utilisation or remove the recorded exceptions. ' + refs)
            elif table['kind'] == 'covenants' and table['rows']:
                statuses = '; '.join(r['covenant'] + ': ' + r['status'] for r in table['rows'])
                result.append('The supplied contractual tests report ' + statuses + '; the headroom shown remains subject to ongoing monitoring. ' + refs)
        if result:
            for c in draft['claim_spans'][1:]:
                if c['kind'] in ('computed', 'computed_summary') and not c.get('ca_edit') and not c.get('ca_input'): self.consumed.add(c['id'])
        return result

    def classification(self):
        draft = self.manifest['sections']['1'].get('draft')
        if not draft: return
        # Only an explicit sourced CA assertion resolves applicability. An absent
        # classification, a satisfactory rating or a low DPD never implies N/A.
        claims = [c for c in draft['claim_spans'][1:] if c.get('ca_edit') or c.get('ca_input')]
        claim = next((c for c in claims if c['text'] == 'The borrower is not classified as Watchlist or Special Mention.'), None)
        cas = self.saved(draft['claim_spans'][1:], 'classification',
            r'The CAS records current classification as Pass, not on Watchlist or Special Mention, and current DPD of 0\.')
        if not claim and cas: claim = cas[0]
        if claim:
            for key in ('s1.classification', 's1.sm_dpd'):
                table = next((t for t in self.copy.report['tables'] if t.get('anchor') == key), None)
                if table:
                    for row in table['rows']:
                        for cell in row:
                            if cell.get('role') == 'value':
                                if key == 's1.classification' and cell['row'] >= 2 and cell['cell'] == 0: continue
                                self.put(key, cell['row'], cell['cell'], 'Not applicable ' + self.refs(claim['evidence_ids']))
            from .word import W, paragraph_text, set_paragraph
            selection = None
            for paragraph in self.table('s1.wrapper').findall(W+'tr/'+W+'tc/'+W+'p'):
                text = paragraph_text(paragraph)
                if text.startswith('[Gap: CA classification'):
                    set_paragraph(paragraph, 'Not applicable — ' + ('CAS classification.' if cas else 'CA classification statement.') + ' ' + self.refs(claim['evidence_ids']))
                elif cas and text.startswith('Is Borrower'):
                    set_paragraph(paragraph, text + '\nNo — Pass; current DPD 0. ' + self.refs(claim['evidence_ids'])); selection = 'dpd'
                elif cas and text.startswith('If Yes, is LOD'):
                    set_paragraph(paragraph, 'LOD question: Not applicable. ' + self.refs(claim['evidence_ids'])); selection = 'lod'
                elif cas and selection and ('Pending CA selection' in text or text in ('☐ Yes', '☐ No')):
                    set_paragraph(paragraph, '')
            if cas:
                self.put('s1.sm_dpd', 0, 1, 'Yes: [ ]')
                self.put('s1.sm_dpd', 0, 2, 'No: [x] ' + self.refs(claim['evidence_ids']))
                self.put('s0.cover', 0, 2, 'Renewal and upsize; Pass; Watchlist / Special Mention: Not applicable. ' + self.refs(claim['evidence_ids']) + '\n[Gap: paper category / ESG Watchlist / AML Greylist confirmation]')

    def request_justification(self, claims):
        from .word import W, paragraph_text, set_paragraph
        wrapper = self.table('s1.wrapper')
        if wrapper is None: return
        c = next((c for c in claims if c['id'] == 'justification'), None)
        for paragraph in wrapper.findall(W+'tr/'+W+'tc/'+W+'p'):
            text = paragraph_text(paragraph)
            if text.startswith('Please insert a screenshot'):
                set_paragraph(paragraph, self.claim(c) if c else '[Gap: request justification]')
                if c: self.consumed.add(c['id'])
            if text.startswith('Please fill up this table'):
                set_paragraph(paragraph, 'Classification table applies to Watchlist or Special Mention borrowers.')

    @staticmethod
    def metric_label(metric):
        return {'cf_profit_before_tax': 'Cash flow starting profit before tax',
                'cf_operating': 'Operating cash flow', 'cf_investing': 'Investing cash flow',
                'cf_financing': 'Financing cash flow', 'cf_change': 'Change in cash',
                'cf_open': 'Opening cash', 'cf_fx': 'FX effect on cash', 'cf_close': 'Closing cash'}.get(
                    metric, metric.replace('_', ' ').capitalize())

    def visible_gaps(self, sid, gaps):
        if sid != 10: return gaps
        displayed = set()
        table = self.table('s10.financials')
        if table is not None:
            from .word import paragraph_text
            displayed.update(paragraph_text(cells(row)[0]).split(' (')[0] for row in rows(table))
        # The grid already names both supported values and missing fields. Do
        # not repeat those field gaps in commentary; the complete input gaps
        # remain in the manifest. Keep absent non-grid metrics visible.
        if self.table('s10.sensitivity') is not None:
            displayed.update(('10% decrease in EBITDA', '100 bp increase in interest rates'))
        if 's4.portfolio' in self.fills: displayed.add('Portfolio valuation')
        if any(g.startswith('Income / balance sheet:') for g in gaps):
            displayed.update(('Financial statements', 'Interest coverage sensitivity'))
        if getattr(self, 'financial_values', {}):
            displayed.update(('Unitholders’ funds', 'Income / balance sheet'))
        return [('Debt maturity buckets: disclosed profile not mapped' if g.startswith('Debt maturity profile:') else g)
                for g in gaps if g.split(':', 1)[0].split(' (')[0] not in displayed]

    def historical_repayment(self, claims):
        candidates = [c for c in claims if c.get('value', {}).get('metric') == 'npi'
                      and c['value']['unit'] == 'currency' and c['value']['currency'] == 'SGD'
                      and c['value']['scope'] == 'Group' and not c['value']['proxy']]
        periods = sorted({c['value']['period'] for c in candidates})
        if len(periods) <= 2:
            for c in candidates:
                v = c['value']; ci = periods.index(v['period']) + 1
                self.put('s9.debt_service', 0, ci, 'Group FY' + v['period'])
                self.put('s9.debt_service', 1, ci, number(Decimal(v['value']) / Decimal(1000000)) + ' ' + self.refs(c['evidence_ids']))
        for c in claims:
            v = c.get('value', {})
            if v.get('metric') == 'interest_coverage' and not v.get('proxy'):
                year = v['period'][:4]
                if year in periods:
                    self.put('s9.debt_service', 3, periods.index(year)+1, number(v['value'], 'times') + ' (reported group) ' + self.refs(c['evidence_ids']))

    def money(self, millions):
        """Show an SGD million amount in the unit the template's financial table states."""
        if getattr(self, 'thousands', False):
            return format((Decimal(millions) * 1000).quantize(Decimal(1), rounding=ROUND_HALF_UP), ',')
        return number(millions)

    def financial_period_columns(self, claims):
        from .word import paragraph_text
        table = self.table('s10.financials')
        self.thousands = table is not None and "'000" in paragraph_text(cells(rows(table)[0])[0])
        periods = set()
        for c in claims:
            period = c.get('value', {}).get('period', '')
            if re.fullmatch(r'\d{4}(?:-\d{2}-\d{2})?', period): periods.add(period[:4])
            if c['id'] in ('portfolio-wale-10', 'occupancy-commentary') and not c.get('ca_edit'):
                periods.update(re.findall(r'31 December (\d{4})', c['text']))
        self.period_columns = {p:i for i,p in enumerate(sorted(periods)[-3:], 1)}
        for ci in (1,2,3):
            self.put('s10.financials',0,ci,'Not used' if periods and ci > len(self.period_columns) else 'Other FY')
            if periods and ci > len(self.period_columns):
                for ri, row in enumerate(rows(self.table('s10.financials'))):
                    if ri and len(cells(row)) == 6: self.put('s10.financials',ri,ci,'—')
        self.put('s10.financials',0,4,'Interim')
        for period, ci in self.period_columns.items(): self.put('s10.financials',0,ci,'FY'+period)

    def record_total(self, key, values):
        table = self.table(key)
        if table is None: return
        fill_row(rows(table)[-1], values)
        self.fills[key]['total'] = values
        original = next(t for t in self.copy.report['tables'] if t.get('anchor') == key)
        prefix = f"{key}.r{len(original['rows'])-1}."
        self.gaps[:] = [g for g in self.gaps if not g.get('anchor', '').startswith(prefix)]
