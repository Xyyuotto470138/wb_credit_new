"""B05 snapshot, dismissal and plain-text request list; no search side effects."""
from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, ConfigDict, Field

from ..services.locks import WorkflowConflict
from .. import schemas as s
from ..repository import Repository
from ..services.gaps import GapService, key, request_list
from ..services.readiness import ReadinessService


class DismissRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    actor: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    role: str = 'CA'


def readiness_router(sessions=None):
    router = APIRouter(prefix='/cases/{case_id}', tags=['readiness'])

    def run(case_id, operation):
        if sessions is None:
            raise HTTPException(503, 'Case persistence is not configured')
        with sessions() as session:
            try:
                session.connection().exec_driver_sql('BEGIN IMMEDIATE')
                repo = Repository(session)
                try:
                    repo.get(s.Case, case_id)
                except ValueError:
                    raise HTTPException(404, 'Case not found')
                result = operation(repo)
                session.commit()
                return result
            except WorkflowConflict as error:
                raise HTTPException(409, str(error)) from error
            except ValueError as error:
                session.rollback()
                raise HTTPException(422, str(error)) from error

    def snapshot(repo, case_id):
        gaps, sections = ReadinessService(repo).refresh(case_id)
        return dict(case_id=case_id, expected_documents=[e.model_dump(mode='json') | {
            'name': gaps.names[key(e)],
            'satisfied': GapService(repo).satisfied(gaps, e),
        } for e in gaps.expected], sections=sections, gaps=gaps.groups)

    @router.get('/readiness')
    def readiness(case_id: str):
        return run(case_id, lambda repo: snapshot(repo, case_id))

    @router.get('/request-list', response_class=PlainTextResponse)
    def export_requests(case_id: str):
        content = run(case_id, lambda repo: request_list(ReadinessService(repo).refresh(case_id)[0]))
        return PlainTextResponse(content, headers={'Content-Disposition': 'attachment; filename="wb-credit-request-list.txt"'})

    @router.post('/expected-documents/{expected_id}/dismiss')
    def dismiss(case_id: str, expected_id: str, request: DismissRequest):
        if request.role != 'CA':
            raise HTTPException(403, 'Only the CA can dismiss an expected document')

        def operation(repo):
            GapService(repo).dismiss(case_id, expected_id, actor=request.actor, reason=request.reason)
            return snapshot(repo, case_id)
        return run(case_id, operation)

    @router.post('/expected-documents/{expected_id}/restore')
    def restore(case_id: str, expected_id: str, request: DismissRequest):
        if request.role != 'CA':
            raise HTTPException(403, 'Only the CA can restore an expected document')
        if not request.actor.strip() or not request.reason.strip():
            raise HTTPException(422, 'Actor and reason are required')

        def operation(repo):
            GapService(repo).restore(case_id, expected_id)
            return snapshot(repo, case_id)
        return run(case_id, operation)

    return router
