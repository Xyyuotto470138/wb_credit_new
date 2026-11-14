"""Build a fresh, offline demo draft and pinned Word bundle; no server/network.

Run from the repository root with the project Python. Owner templates and source
packs are read only. Use a new output directory for each standalone run.
"""
import argparse
import json
from pathlib import Path
import sys
from datetime import datetime, timezone
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
DEMO_CA_POSITION = ('Support the renewal and upsize, subject to an updated valuation before drawdown, '
                    'LTV covenant monitoring and satisfaction of the prior approval conditions.')
sys.path.insert(0,str(ROOT))

from backend.app import schemas as s
from backend.app.database import create_database
from backend.app.exports import ExportService, ExportRequest
from backend.app.local import demo_settings
from backend.app.repository import Repository
from backend.app.services.drafting import DraftingService, DraftRequest
from backend.app.services.intake import IntakeService
from backend.app.services.search import SavedPublicPackProvider
from backend.app.services.search.service import PublicSearchService
from backend.app.services.templates import TemplateRegistry
from backend.app.team_config import load_team
from backend.app.llm.client import MockProvider, request_key
from backend.app.extraction_agent.orchestrator import messages
from backend.app.services.spreading import SpreadingService, SpreadRequest


def saved_spread(repo, case, storage):
    """Explicit saved B09 fixture, identical validation path to the local demo."""
    from backend.app.api.demo import REPORT_HASH
    doc = next(d for d in repo.list_for_case(s.Document, case.id)
               if d.content_hash == REPORT_HASH and d.catalogue_id == 4)
    provider = MockProvider()
    service = SpreadingService(repo, storage, provider)
    index = service.evidence.index_document(case.id, doc.id)
    ids = {f'page:{e.page}': e.id for ref in index.evidence_ids
           if (e := repo.get(s.Evidence, ref)).page in (127, 128, 155, 156, 162)}
    request = SpreadRequest(profile='reit_core', evidence_ids=list(ids.values()), periods=['2025', '2024'], scope='Group')
    _, profile, sources, _ = service.prepare(case.id, request)
    response = json.loads((ROOT/'backend/app/fixtures/esr-core-response.json').read_text())
    for table in response['tables']:
        for key in ('evidence_id', 'currency_evidence_id'): table[key] = ids[table[key]]
    for action, content, current in [('full', response, None), ('missing_rows', {'tables': []}, response)]:
        provider.fixtures[request_key(messages(action, sources, profile, current), 12000, 0, 60)] = dict(text=json.dumps(content), stop_reason='end_turn', content=[])
    return service.generate(case.id, request)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',default='runtime/b18/standalone')
    parser.add_argument('--with-spread', action='store_true', help='Explicitly confirm the saved public demo pack and generate its reviewed mock spread')
    args=parser.parse_args()
    output=(ROOT/args.output).resolve()
    if not output.is_relative_to(ROOT/'runtime'):
        parser.error('Use a directory inside this repository runtime/')
    if output.exists():
        parser.error('Use a new output directory; existing exports are never overwritten')
    output.mkdir(parents=True)
    engine,sessions=create_database(output/'demo.sqlite')
    try:
        with sessions.begin() as session:
            session.connection().exec_driver_sql('BEGIN IMMEDIATE')
            repo=Repository(session);config=load_team('fig')
            fixture,folders,options,_=demo_settings()
            case=repo.save(s.Case(borrower_name=fixture['borrower']['name'],
                config_hash=config.content_hash,config_version=config.template.version,**fixture['app_case']))
            intake=IntakeService(repo,output/'blobs',folders)
            for option in options:
                intake.scan(case.id,option['id'],option['metadata_by_path'])
            search = PublicSearchService(repo,output/'blobs',SavedPublicPackProvider())
            search.search(case.id)
            if args.with_spread:
                for document in repo.list_for_case(s.Document, case.id):
                    if document.origin == 'public': search.confirm(case.id, document.id, actor='synthetic-demo-ca')
                saved_spread(repo, case, output/'blobs')
            TemplateRegistry(repo,output/'templates').seed_owner_templates('fig',ROOT)
            drafting=DraftingService(repo,output/'blobs',output/'templates')
            for sid in [1,2,3,4,5,6,7,8,10,9,11,12,13,14]:
                # The fictional CA position is dated 10 November in this saved
                # demonstration. Normal application requests use the actual clock.
                with patch.object(s, 'utcnow', return_value=datetime(2026, 11, 10, 9, tzinfo=timezone.utc)):
                    drafting.generate(case.id,sid,DraftRequest(actor='synthetic-demo-ca',confirm_unsecured=True,
                        ca_position=DEMO_CA_POSITION if sid==14 else None))
            service=ExportService(repo,output/'blobs',output/'templates',output/'exports')
            manifest,_=service.prepare(case.id)
            artifact=service.create(case.id,ExportRequest(actor='synthetic-demo-ca',expected_preview_token=manifest['preview_token']))
            (output/'draft.docx').write_bytes(service.content(case.id,artifact.id))
            (output/'manifest.json').write_text(json.dumps(artifact.manifest,ensure_ascii=False,indent=2))
            (output/'request-list.txt').write_text(artifact.manifest['request_list'])
            print(json.dumps(dict(case_id=case.id,export_id=artifact.id,output=str(output.relative_to(ROOT)),
                mapping_gaps=len(artifact.manifest['mapping_gaps']),cost_usd=0)))
    finally:
        engine.dispose()


if __name__=='__main__':
    main()
