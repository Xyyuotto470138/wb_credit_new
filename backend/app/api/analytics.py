"""Explicit reviewed source mappings and immutable Python computation snapshots."""
from fastapi import APIRouter, HTTPException

from ..services.locks import WorkflowConflict
from .. import schemas as s
from ..repository import Repository
from ..retrieval.service import ContentIntegrityError, EvidenceNotFound
from ..analytics import AnalyticsRequest, AnalyticsService
from ..analytics.engine import VERSION


def analytics_router(sessions=None, storage_root=None):
    router = APIRouter(prefix='/cases/{case_id}/analytics', tags=['computed tables'])

    def run(case_id, operation, write=False):
        if sessions is None or storage_root is None:
            raise HTTPException(503, 'Computation persistence is not configured')
        with sessions() as session:
            try:
                if write:
                    session.connection().exec_driver_sql('BEGIN IMMEDIATE')
                repo = Repository(session)
                repo.get(s.Case, case_id)
                result = operation(AnalyticsService(repo, storage_root))
                session.commit()
                return result
            except WorkflowConflict as error:
                raise HTTPException(409, str(error)) from error
            except ContentIntegrityError as error:
                raise HTTPException(409, str(error)) from error
            except EvidenceNotFound as error:
                raise HTTPException(404, str(error)) from error
            except ValueError as error:
                raise HTTPException(422, str(error)) from error

    @router.post('')
    def generate(case_id: str, request: AnalyticsRequest):
        return run(case_id, lambda service: service.generate(case_id, request), True)

    @router.get('')
    def listing(case_id: str):
        return run(case_id, lambda service: [r for r in service.repo.list_for_case(s.Spread, case_id) if r.version == VERSION])

    @router.get('/{spread_id}')
    def get(case_id: str, spread_id: str):
        return run(case_id, lambda service: service.get(case_id, spread_id))

    return router
