"""B08 indexing/retrieval writes are explicit; source resolution is read-only."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from .. import schemas as s
from ..repository import Repository
from ..retrieval import EvidenceService, RetrievalRequest
from ..retrieval.service import ContentIntegrityError, EvidenceNotFound


class RegionRequest(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)
    bbox: list[float] = Field(min_length=4, max_length=4)


def evidence_router(sessions=None, storage_root=None):
    router = APIRouter(prefix='/cases/{case_id}', tags=['page evidence'])

    def run(case_id, operation, *, write=False):
        if sessions is None or storage_root is None:
            raise HTTPException(503, 'Evidence persistence is not configured')
        with sessions() as session:
            try:
                if write:
                    session.connection().exec_driver_sql('BEGIN IMMEDIATE')
                repo = Repository(session)
                try:
                    repo.get(s.Case, case_id)
                except ValueError:
                    raise EvidenceNotFound('Case not found')
                result = operation(EvidenceService(repo, storage_root))
                session.commit()
                return result
            except EvidenceNotFound as error:
                raise HTTPException(404, str(error)) from error
            except ContentIntegrityError as error:
                raise HTTPException(409, str(error)) from error
            except ValueError as error:
                raise HTTPException(422, str(error)) from error

    @router.post('/documents/{document_id}/index')
    def index(case_id: str, document_id: str):
        return run(case_id, lambda service: service.index_document(case_id, document_id), write=True)

    @router.post('/sections/{section_id}/evidence')
    def retrieve(case_id: str, section_id: int, request: RetrievalRequest):
        return run(case_id, lambda service: service.retrieve(case_id, section_id, request), write=True)

    @router.get('/evidence/{evidence_id}')
    def resolve(case_id: str, evidence_id: str):
        return run(case_id, lambda service: service.resolve(case_id, evidence_id))

    @router.post('/evidence/{evidence_id}/regions')
    def region(case_id: str, evidence_id: str, request: RegionRequest):
        return run(case_id, lambda service: service.cite_pdf_region(case_id, evidence_id, request.bbox), write=True)

    @router.get('/citations/{citation_id}')
    def citation(case_id: str, citation_id: str):
        return run(case_id, lambda service: service.resolve_citation(case_id, citation_id))

    return router
