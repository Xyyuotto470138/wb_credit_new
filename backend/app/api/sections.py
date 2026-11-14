"""B13 section history and explicit version operations, serialized in SQLite."""
from fastapi import APIRouter, HTTPException

from .. import schemas as s
from ..repository import Repository
from ..llm.client import LiveProviderDisabled
from ..retrieval.service import ContentIntegrityError
from ..services.templates import TemplateIntegrityError
from ..es2.blocks import BlockRequest, apply as apply_block
from ..es2 import updates
from ..services.versions import VersionService, VersionRequest, EditRequest, RedraftRequest, RevisionConflict


def sections_router(sessions=None, storage_root=None, template_storage_root=None, provider=None):
    router = APIRouter(prefix='/cases/{case_id}/sections', tags=['section versions'])

    def run(case_id, operation):
        if sessions is None or storage_root is None:
            raise HTTPException(503, 'Section persistence is not configured')
        with sessions() as session:
            try:
                session.connection().exec_driver_sql('BEGIN IMMEDIATE')
                repo = Repository(session)
                repo.get(s.Case, case_id)
                result = operation(VersionService(repo, storage_root, template_storage_root, provider))
                session.commit()
                return result
            except (RevisionConflict, ContentIntegrityError, TemplateIntegrityError) as error:
                raise HTTPException(409, str(error)) from error
            except (ValueError, LiveProviderDisabled) as error:
                raise HTTPException(422, str(error)) from error

    @router.get('')
    def listing(case_id: str):
        return run(case_id, lambda service: service.sections(case_id))

    @router.get('/updates')
    def update_overview(case_id: str):
        """New documents and the sections they affect, with any proposal waiting for the maker."""
        return run(case_id, lambda service: updates.overview(service, case_id))

    @router.post('/{section_id}/update-proposal')
    def update_propose(case_id: str, section_id: int, request: VersionRequest):
        """Prepare a proposed update of one affected section. The section is not changed. This calls the drafting model."""
        return run(case_id, lambda service: updates.propose(service, case_id, section_id, request))

    @router.post('/update-proposals/{proposal_id}/apply')
    def update_apply(case_id: str, proposal_id: str, request: updates.ApplyRequest):
        return run(case_id, lambda service: updates.apply(service, case_id, proposal_id, request))

    @router.post('/update-proposals/{proposal_id}/dismiss')
    def update_dismiss(case_id: str, proposal_id: str, request: updates.DismissRequest):
        return run(case_id, lambda service: updates.dismiss(service, case_id, proposal_id, request))

    @router.get('/{section_id}/history')
    def history(case_id: str, section_id: int):
        return run(case_id, lambda service: service.history(case_id, section_id))

    @router.post('/{section_id}/save')
    def save(case_id: str, section_id: int, request: EditRequest):
        return run(case_id, lambda service: service.save(case_id, section_id, request))

    @router.post('/{section_id}/redraft')
    def redraft(case_id: str, section_id: int, request: RedraftRequest):
        return run(case_id, lambda service: service.redraft(case_id, section_id, request))

    @router.post('/{section_id}/confirm')
    def confirm(case_id: str, section_id: int, request: VersionRequest):
        return run(case_id, lambda service: service.confirm(case_id, section_id, request))

    @router.post('/{section_id}/blocks')
    def blocks(case_id: str, section_id: int, request: BlockRequest):
        """Add, change, move or remove analyst added content. Each change is a new version of the section."""
        return run(case_id, lambda service: apply_block(service, storage_root, case_id, section_id, request))

    return router
