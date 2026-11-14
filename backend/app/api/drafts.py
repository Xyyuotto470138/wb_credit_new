"""B11/B12 drafts and immutable preview export; Word ES export belongs to B18."""
from fastapi import APIRouter, HTTPException, Response

from ..services.locks import WorkflowConflict
from .. import schemas as s
from ..repository import Repository
from ..llm.client import LiveProviderDisabled
from ..retrieval.service import ContentIntegrityError
from ..services.templates import TemplateIntegrityError
from ..services.drafting import DraftingService, DraftRequest


def drafts_router(sessions=None, storage_root=None, template_storage_root=None, provider=None):
    router = APIRouter(prefix='/cases/{case_id}/drafts', tags=['section drafts'])

    def run(case_id, operation, write=False):
        if sessions is None or storage_root is None:
            raise HTTPException(503, 'Draft persistence is not configured')
        with sessions() as session:
            try:
                if write:
                    session.connection().exec_driver_sql('BEGIN IMMEDIATE')
                repo = Repository(session)
                repo.get(s.Case, case_id)
                result = operation(DraftingService(repo, storage_root, template_storage_root, provider))
                session.commit()
                return result
            except WorkflowConflict as error:
                raise HTTPException(409, str(error)) from error
            except (ContentIntegrityError, TemplateIntegrityError) as error:
                raise HTTPException(409, str(error)) from error
            except (ValueError, LiveProviderDisabled) as error:
                raise HTTPException(422, str(error)) from error

    @router.get('')
    def listing(case_id: str):
        return run(case_id, lambda service: service.repo.list_for_case(s.DraftVersion, case_id))

    @router.post('/sections/{section_id}')
    def generate(case_id: str, section_id: int, request: DraftRequest):
        return run(case_id, lambda service: service.generate(case_id, section_id, request), True)

    @router.get('/{draft_id}')
    def get(case_id: str, draft_id: str):
        return run(case_id, lambda service: service.get(case_id, draft_id))

    @router.get('/{draft_id}/preview.txt')
    def export(case_id: str, draft_id: str):
        draft = run(case_id, lambda service: service.get(case_id, draft_id))
        return Response(draft['text'], media_type='text/plain', headers={
            'Content-Disposition': f'attachment; filename="section-{draft["section_id"]}-mock-preview.txt"'})

    return router
