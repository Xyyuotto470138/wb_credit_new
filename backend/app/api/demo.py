"""Explicit local-only saved-pack spread demonstration; never a live fallback.

Mounted by local.create_demo_app only. Generic application/provider APIs retain
their existing contracts. The reviewed B09 response is copied into app fixtures.
"""
import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

from ..services.locks import WorkflowConflict, require_working
from .gaps import CARequest
from .. import schemas as s
from ..extraction_agent.orchestrator import messages
from ..llm.client import MockProvider, request_key
from ..repository import Repository
from ..retrieval.service import ContentIntegrityError
from ..services.gaps import current_documents
from ..services.spreading import SpreadingService, SpreadRequest

REPORT_HASH = '638f8d635d2ebc15d6171a95f04e4d7194273e80fe5b5db5d3671f7a755c811b'


def demo_router(sessions, storage_root, demo_case_id):
    router = APIRouter(tags=['local offline demo'])

    @router.post('/cases/{case_id}/demo/spread')
    def spread(case_id: str, request: CARequest):
        if case_id != demo_case_id:
            raise HTTPException(404, 'Saved spread demo is unavailable for this case')
        if request.role != 'CA':
            raise HTTPException(403, 'Only the CA can generate the demo spread')
        if not request.actor.strip():
            raise HTTPException(422, 'Actor is required')
        with sessions() as session:
            try:
                session.connection().exec_driver_sql('BEGIN IMMEDIATE')
                repo = Repository(session)
                case = repo.get(s.Case, case_id)
                require_working(repo, case_id)
                docs = [d for d in current_documents(repo.list_for_case(s.Document, case_id), case)
                        if d.content_hash == REPORT_HASH and d.catalogue_id == 4]
                if len(docs) != 1 or not docs[0].confirmed_by:
                    raise ValueError('Review and confirm the saved FY2025 annual report before generating the mock spread')
                provider = MockProvider()
                service = SpreadingService(repo, storage_root, provider)
                index = service.evidence.index_document(case_id, docs[0].id)
                ids = {f'page:{e.page}': e.id for ref in index.evidence_ids
                       if (e := repo.get(s.Evidence, ref)).page in (127, 128, 155, 156, 162)}
                if len(ids) != 5:
                    raise ValueError('Saved spread source pages unavailable')
                command = SpreadRequest(profile='reit_core', evidence_ids=list(ids.values()),
                                        periods=['2025', '2024'], scope='Group')
                _, profile, sources, _ = service.prepare(case_id, command)
                response = json.loads((Path(__file__).resolve().parents[1] / 'fixtures/esr-core-response.json').read_text())
                for table in response['tables']:
                    table['evidence_id'] = ids[table['evidence_id']]
                    table['currency_evidence_id'] = ids[table['currency_evidence_id']]
                for action, content, current in [('full', response, None), ('missing_rows', {'tables': []}, response)]:
                    key = request_key(messages(action, sources, profile, current), 12000, 0, 60)
                    provider.fixtures[key] = dict(text=json.dumps(content), stop_reason='end_turn', content=[])
                result = service.generate(case_id, command)
                session.commit()
                return result
            except WorkflowConflict as error:
                raise HTTPException(409, str(error)) from error
            except ContentIntegrityError as error:
                raise HTTPException(409, str(error)) from error
            except (ValueError, OSError, KeyError) as error:
                raise HTTPException(422, str(error)) from error

    return router
