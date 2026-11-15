"""Review threads on a paper: open, reply, resolve with a conclusion, reopen."""
from fastapi import APIRouter, HTTPException

from .. import schemas as s
from ..repository import Repository
from ..services import threads


def threads_router(sessions=None):
    router = APIRouter(prefix='/cases/{case_id}/threads', tags=['review threads'])

    def run(case_id, operation):
        if sessions is None:
            raise HTTPException(503, 'Case persistence is not configured')
        with sessions() as session:
            session.connection().exec_driver_sql('BEGIN IMMEDIATE')
            repo = Repository(session)
            try:
                repo.get(s.Case, case_id)
            except ValueError:
                raise HTTPException(404, 'Case not found')
            try:
                result = operation(repo)
            except ValueError as error:
                raise HTTPException(422, str(error)) from error
            session.commit()
            return result

    @router.get('')
    def listing(case_id: str):
        return run(case_id, lambda repo: threads.listing(repo, case_id))

    @router.post('', status_code=201)
    def open_thread(case_id: str, request: threads.OpenRequest):
        return run(case_id, lambda repo: threads.open_thread(repo, case_id, request))

    @router.post('/{thread_id}/replies')
    def reply(case_id: str, thread_id: str, request: threads.Said):
        return run(case_id, lambda repo: threads.reply(repo, case_id, thread_id, request))

    @router.post('/{thread_id}/resolve')
    def resolve(case_id: str, thread_id: str, request: threads.ResolveRequest):
        return run(case_id, lambda repo: threads.resolve(repo, case_id, thread_id, request))

    @router.post('/{thread_id}/reopen')
    def reopen(case_id: str, thread_id: str, request: threads.ReopenRequest):
        return run(case_id, lambda repo: threads.reopen(repo, case_id, thread_id, request))

    return router
