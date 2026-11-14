"""Prototype role-switcher API, not authentication or bank entitlements."""
from fastapi import APIRouter, HTTPException

from .. import schemas as s
from ..repository import Repository
from ..retrieval.service import ContentIntegrityError
from ..services.templates import TemplateIntegrityError
from ..services.locks import WorkflowConflict
from ..services.submission_checks import SubmissionConflict
from ..services.workflow import WorkflowService, WorkflowPermission, TransitionRequest


def workflow_router(sessions=None, storage_root=None, template_storage_root=None):
    router = APIRouter(prefix='/cases/{case_id}/workflow', tags=['workflow'])

    def run(case_id, operation):
        if sessions is None or storage_root is None or template_storage_root is None:
            raise HTTPException(503, 'Workflow persistence/storage is not configured')
        with sessions() as session:
            try:
                session.connection().exec_driver_sql('BEGIN IMMEDIATE')
                repo = Repository(session)
                try:
                    repo.get(s.Case, case_id)
                except ValueError:
                    raise HTTPException(404, 'Case not found')
                result = operation(WorkflowService(repo, storage_root, template_storage_root))
                session.commit()
                return result
            except WorkflowPermission as error:
                raise HTTPException(403, str(error)) from error
            except SubmissionConflict as error:
                raise HTTPException(409, dict(message=str(error), report=error.report)) from error
            except (WorkflowConflict, ContentIntegrityError, TemplateIntegrityError) as error:
                raise HTTPException(409, str(error)) from error
            except ValueError as error:
                raise HTTPException(422, str(error)) from error

    @router.get('')
    def view(case_id: str):
        return run(case_id, lambda service: service.view(case_id))

    @router.post('/transitions')
    def transition(case_id: str, request: TransitionRequest):
        return run(case_id, lambda service: service.transition(case_id, request))

    @router.get('/snapshots/{es_id}')
    def snapshot(case_id: str, es_id: str):
        return run(case_id, lambda service: service.snapshot(case_id, es_id))

    return router
