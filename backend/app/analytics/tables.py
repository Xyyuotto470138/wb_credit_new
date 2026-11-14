"""Strict source-extract adapters for B03's documented workbook contracts.

Unknown layouts are gaps. All cells retain original worksheet/cell locations;
source totals and ratios are reconciliation controls, never substituted outputs.
"""
from calendar import monthrange
from datetime import date
from decimal import Decimal as D
from .engine import number, display

HEADERS = {
 'exposure': ['Facility','Existing limit','Outstanding','Proposed limit','Change','Existing maturity','Proposed maturity','Security'],
 'covenants': ['Metric','Actual','Limit','Direction','Headroom','Unit','Test date','Source'],
 'monthly': ['Month end','Facility','Limit','Month-end outstanding','Monthly peak outstanding'],
 'events': ['Event','Facility','Start or due date','End or paid date','Amount SGD m','Cured date','Description'],
 'projections': ['Year','Rent','Operating costs','NPI','Other reserve','Capex reserve','Cash for debt service','Interest','Bullet principal','Debt service','DSCR x'],
}


def day(value):
    return date.fromisoformat(value[:10])


class Sheet:
    def __init__(self, source, kind):
        self.source, self.kind = source, kind
        loc = source['locator']
        rows = loc.get('rows', [])
        matches = [i for i,r in enumerate(rows) if r == HEADERS[kind]]
        if loc.get('format') != 'xlsx' or loc.get('formula_cells') or len(matches) != 1:
            raise ValueError(f'{kind}: unsupported/ambiguous worksheet layout or unevaluated formulas')
        self.start = matches[0] + 1
        self.rows = [(i+1,r) for i,r in enumerate(rows) if i >= self.start and any(r)]
        if not self.rows and kind != 'events':
            raise ValueError(f'{kind}: no source rows')
        self.context = '\n'.join('\t'.join(r) for r in rows[:self.start-1])
        if kind in ('exposure','monthly','projections') and 'SGD million' not in self.context:
            raise ValueError('Unknown currency/scale in worksheet')
        if kind == 'events' and 'Complete synthetic event register' not in self.context:
            raise ValueError('Event-register completeness needs explicit evidence')
        if kind == 'monthly' and 'Month-end samples' not in self.context:
            raise ValueError('Sampling basis needs explicit evidence')

    def cells(self, rownum, row, columns):
        return {f'{self.source["evidence_id"]}:{rownum}:{c+1}': number(row[c]) for c in columns}

    def refs(self):
        return [self.source['evidence_id']]


def compute_table(kind, sources, case):
    table = dict(kind=kind, section_id=2 if kind=='exposure' else 9 if kind=='projections' else 13,
                 rows=[], cells=[], gaps=[], source_register=sources)
    sheets=[]
    def emit(key, value, operands, used, unit='currency_million', period='', scope='', gap=None):
        refs=sorted({ref for sh in used for ref in sh.refs()})
        cell=dict(metric=key,name=key,unit=unit,period=period,scope=scope,currency='SGD' if unit=='currency_million' else None,
                  value=None if value is None else str(value),display=display(value),gaps=[gap] if gap else [],
                  operands={k:str(v) for k,v in operands.items()},operand_evidence_ids={k:refs for k in operands},
                  synthetic=any(sh.source['synthetic'] for sh in used),proxy=False,thresholds=[],details={},sources={})
        table['cells'].append(cell)
        return cell['value']
    def div(a,b):
        if b <= 0: return None
        return a/b
    try:
        if kind != 'conduct' and len(sources) != 1:
            raise ValueError('Select exactly one complete source worksheet')
        if kind == 'exposure':
            sh=Sheet(sources[0],kind); sheets=[sh]
            details=[(n,r) for n,r in sh.rows if r[0] != 'Total']
            controls=[r for _,r in sh.rows if r[0]=='Total']
            if len(controls)!=1 or not details or len({r[0] for _,r in details})!=len(details):
                raise ValueError('Exposure requires unique facilities and one total control')
            if case.new_to_bank and any(number(r[1]) or number(r[2]) for _,r in details):
                raise ValueError('Nonzero existing exposure conflicts with new-to-bank input')
            sums=[D(0)]*4; allops={}
            for n,r in details:
                ops=sh.cells(n,r,range(1,4)); allops.update(ops)
                existing,outstanding,proposed=map(number,r[1:4])
                if min(existing,outstanding,proposed)<0: raise ValueError('Negative exposure')
                change=proposed-existing
                if change!=number(r[4]): raise ValueError('Exposure change control mismatch')
                for i,v in enumerate((existing,outstanding,proposed,change)): sums[i]+=v
                row=dict(facility=r[0],entity=case.borrower_name,currency='SGD',period=sh.source['period'],
                         existing_maturity=day(r[5]).isoformat(),proposed_maturity=day(r[6]).isoformat(),security=r[7])
                for key,v in zip(('existing','outstanding','proposed','increase','undrawn_existing','existing_utilisation_pct'),
                                 (existing,outstanding,proposed,change,existing-outstanding,div(outstanding*100,existing))):
                    row[key]=emit(f'exposure/{r[0]}/{key}',v,ops,[sh],unit='percent' if key.endswith('_pct') else 'currency_million',
                                  period=sh.source['period'],scope=case.borrower_name,gap='Zero existing limit: utilisation unavailable' if v is None else None)
                table['rows'].append(row)
            if sums!=list(map(number,controls[0][1:5])): raise ValueError('Exposure total control mismatch')
            table['totals']={}
            for key,v in zip(('existing','outstanding','proposed','increase','undrawn_existing','existing_utilisation_pct'),
                             (*sums,sums[0]-sums[1],div(sums[1]*100,sums[0]))):
                table['totals'][key]=emit('exposure/total/'+key,v,allops,[sh],unit='percent' if key.endswith('_pct') else 'currency_million',
                    period=sh.source['period'],scope=case.borrower_name,gap='Zero existing limit: utilisation unavailable' if v is None else None)
        elif kind == 'covenants':
            sh=Sheet(sources[0],kind); sheets=[sh]
            if len({r[0] for _,r in sh.rows})!=len(sh.rows): raise ValueError('Duplicate covenant')
            for n,r in sh.rows:
                actual,limit=map(number,r[1:3]); direction=r[3]
                if direction not in ('maximum','minimum'): raise ValueError('Unknown covenant direction')
                headroom=limit-actual if direction=='maximum' else actual-limit
                if headroom!=number(r[4]): raise ValueError('Covenant headroom control mismatch')
                if r[5] not in ('percentage points','times'): raise ValueError('Unknown covenant units')
                ops=sh.cells(n,r,(1,2))
                table['rows'].append(dict(covenant=r[0],actual=str(actual),limit=str(limit),direction=direction,
                    test_date=day(r[6]).isoformat(),source_note=r[7],
                    headroom=emit('covenant/'+r[0],headroom,ops,[sh],unit=r[5],period=day(r[6]).isoformat(),scope=r[0]),
                    status='within contractual threshold' if headroom>=0 else 'outside contractual threshold',
                    classification='Contractual test; not a regulatory determination'))
        elif kind == 'projections':
            sh=Sheet(sources[0],kind); sheets=[sh]
            if len({r[0] for _,r in sh.rows})!=len(sh.rows): raise ValueError('Duplicate projection year')
            for n,r in sh.rows:
                ops=sh.cells(n,r,(1,2,4,5,7,8))
                rent,cost,reserve,capex,interest,principal=[number(r[i]) for i in (1,2,4,5,7,8)]
                if min(cost,reserve,capex,interest,principal)<0: raise ValueError('Negative projection expense or repayment')
                npi=rent-cost; cash=npi-reserve-capex; service=interest+principal; dscr=div(cash,service)
                if [npi,cash,service]!=[number(r[i]) for i in (3,6,9)]: raise ValueError('Projection control mismatch')
                if dscr is not None and abs(dscr-number(r[10]))>D('.000001'): raise ValueError('DSCR control mismatch')
                row=dict(year=r[0],basis='Property projection; not consolidated group forecast')
                for key,v in dict(npi=npi,cash_for_debt_service=cash,interest=interest,principal=principal,debt_service=service,dscr=dscr).items():
                    row[key]=emit('projection/'+r[0]+'/'+key,v,ops,[sh],unit='times' if key=='dscr' else 'currency_million',period=r[0],scope=sh.context,
                                  gap='Zero debt service denominator' if v is None else None)
                table['rows'].append(row)
        elif kind == 'conduct':
            if len(sources)!=2: raise ValueError('Conduct requires both monthly samples and complete events register')
            by_header={tuple(src['locator'].get('rows',[[],[],[],[],[]])[4]):src for src in sources}
            if set(by_header)!={tuple(HEADERS['monthly']),tuple(HEADERS['events'])}: raise ValueError('Select monthly and events sheets')
            monthly=Sheet(by_header[tuple(HEADERS['monthly'])],'monthly')
            events=Sheet(by_header[tuple(HEADERS['events'])],'events'); sheets=[monthly,events]
            # Both sheets must belong to the same immutable report version.
            if monthly.source['document_id']!=events.source['document_id']: raise ValueError('Conduct sheets must share document/version')
            facilities={r[1] for _,r in monthly.rows}
            if any(r[1] not in facilities for _,r in events.rows): raise ValueError('Event references unknown facility')
            dates_by_facility=[]
            for facility in sorted(facilities):
                sample=[(n,r) for n,r in monthly.rows if r[1]==facility]
                dates=sorted(day(r[0]) for _,r in sample); dates_by_facility.append(dates)
                if len(dates)!=12 or len(set(dates))!=12 or any(d.day!=monthrange(d.year,d.month)[1] for d in dates):
                    raise ValueError('Conduct needs 12 unique month-end observations')
                if any((b.year*12+b.month)-(a.year*12+a.month)!=1 for a,b in zip(dates,dates[1:])): raise ValueError('Missing conduct months')
                start=dates[0].replace(day=1); end=dates[-1]
                coverage=f'{start.day} {start:%b %Y} to {end.day} {end:%b %Y}'
                if coverage not in events.context:
                    raise ValueError('Event-register coverage does not match monthly reporting window')
                limits=[number(r[2]) for _,r in sample]; balances=[number(r[3]) for _,r in sample]; peaks=[number(r[4]) for _,r in sample]
                if any(l<=0 or b<0 or p<b for l,b,p in zip(limits,balances,peaks)): raise ValueError('Invalid monthly limit/balance/peak')
                ops={k:v for n,r in sample for k,v in monthly.cells(n,r,(2,3,4)).items()}
                event_rows=[(n,r) for n,r in events.rows if r[1]==facility]
                excess=[]; late=[]; excess_dates=set(); unique=set()
                for n,r in event_rows:
                    event,a,b,amount=r[0],day(r[2]),day(r[3]),number(r[4])
                    sig=tuple(r)
                    if sig in unique or not start<=a<=b<=end or amount<0 or event not in ('Excess','Past due'): raise ValueError('Invalid or duplicate event/date')
                    if r[5] and day(r[5]) < b: raise ValueError('Cure date precedes event end/payment date')
                    unique.add(sig); ops.update(events.cells(n,r,(4,)))
                    ops[f'event:{n}:start_ordinal']=D(a.toordinal()); ops[f'event:{n}:end_ordinal']=D(b.toordinal())
                    if event=='Excess':
                        excess.append((a,b,amount)); excess_dates.update(range(a.toordinal(),b.toordinal()+1))
                    else: late.append((a,b,amount))
                if max((p-l for p,l in zip(peaks,limits)))>0 and not excess: raise ValueError('Monthly peak excess lacks event coverage')
                mean=sum(balances)/len(balances)
                latest=max(sample,key=lambda row:day(row[1][0]))[1]
                stats=dict(limit=number(latest[2]),peak=max(peaks),peak_utilisation_pct=max(p/l*100 for p,l in zip(peaks,limits)),mean_month_end=mean,mean_utilisation_pct=sum(b/l*100 for b,l in zip(balances,limits))/len(limits),
                    excess_count=D(len(excess)),excess_days=D(len(excess_dates)),max_excess=max((e[2] for e in excess),default=D(0)),
                    past_due_count=D(len(late)),max_dpd=D(max(((e[1]-e[0]).days for e in late),default=0)),max_past_due=max((e[2] for e in late),default=D(0)))
                row=dict(facility=facility,period_start=start.isoformat(),period_end=end.isoformat(),
                    average_basis='arithmetic mean of 12 month-end balances; not daily average',
                    events=[dict(zip(HEADERS['events'],r)) for _,r in event_rows])
                for key,v in stats.items():
                    unit='percent' if key.endswith('_pct') else 'count' if key.endswith('count') else 'days' if key in ('excess_days','max_dpd') else 'currency_million'
                    row[key]=emit('conduct/'+facility+'/'+key,v,ops,sheets,unit=unit,period=f'{start}/{end}',scope=facility)
                table['rows'].append(row)
            if any(d!=dates_by_facility[0] for d in dates_by_facility): raise ValueError('Mismatched facility reporting windows')
    except (ValueError, KeyError, IndexError) as error:
        table.update(rows=[],cells=[],gaps=[f'{kind}: {error}'])
        table.pop('totals',None)
    return table
