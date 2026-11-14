"""Maker and checker read model and the checker's section marks. Moves between roles stay in the workflow API."""
from fastapi import APIRouter, HTTPException

from .. import schemas as s
from ..repository import Repository
from ..services import review
from ..services.locks import WorkflowConflict


def review_router(sessions=None):
    router = APIRouter(prefix='/cases/{case_id}/review', tags=['review'])

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
                raise HTTPException(422, str(error)) from error

    @router.get('')
    def get(case_id: str):
        return run(case_id, lambda repo: review.view(repo, case_id))

    @router.post('/marks')
    def mark(case_id: str, request: review.MarkRequest):
        return run(case_id, lambda repo: review.mark(repo, case_id, request))

    return router
