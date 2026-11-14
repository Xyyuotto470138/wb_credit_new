"""B06 explicit search/confirmation actions; request bodies cannot supply queries."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from ..services.locks import WorkflowConflict
from .. import schemas as s
from ..repository import Repository
from ..services.gaps import GapService
from ..services.search import OffProvider, PublicSearchService, generation_offers


class CARequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    actor: str = Field(min_length=1, max_length=200)
    role: str = 'CA'


def gaps_router(sessions=None, storage_root=None, provider=None):
    router = APIRouter(prefix='/cases/{case_id}', tags=['public gaps'])
    provider = provider if provider is not None else OffProvider()

    def run(case_id, operation):
        if sessions is None or storage_root is None:
            raise HTTPException(503, 'Case persistence/content storage is not configured')
        with sessions() as session:
            try:
                session.connection().exec_driver_sql('BEGIN IMMEDIATE')
                repo = Repository(session)
                try:
                    repo.get(s.Case, case_id)
                except ValueError:
                    raise HTTPException(404, 'Case not found')
                result = operation(repo, PublicSearchService(repo, storage_root, provider))
                session.commit()
                return result
            except WorkflowConflict as error:
                raise HTTPException(409, str(error)) from error
            except ValueError as error:
                session.rollback()
                raise HTTPException(422, str(error)) from error

    def authorize(request):
        if request.role != 'CA':
            raise HTTPException(403, 'Only the CA can search or confirm evidence')
        if not request.actor.strip():
            raise HTTPException(422, 'Actor is required')

    @router.post('/public-search')
    def search(case_id: str, request: CARequest):
        authorize(request)
        return run(case_id, lambda repo, service: service.search(case_id))

    @router.post('/documents/{document_id}/confirm')
    def confirm(case_id: str, document_id: str, request: CARequest):
        authorize(request)
        return run(case_id, lambda repo, service: service.confirm(case_id, document_id, actor=request.actor, role=request.role))

    @router.get('/generation-offers')
    def offers(case_id: str):
        return run(case_id, lambda repo, service: generation_offers(GapService(repo).refresh(case_id)))

    return router
