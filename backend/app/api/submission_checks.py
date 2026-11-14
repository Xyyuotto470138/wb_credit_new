"""Pre-submission preview, recorded results and enforcing gate; no workflow moves."""
from fastapi import APIRouter, HTTPException

from .. import schemas as s
from ..repository import Repository
from ..services.locks import WorkflowConflict
from ..retrieval.service import ContentIntegrityError
from ..services.templates import TemplateIntegrityError
from ..services.submission_checks import CheckRequest, SubmissionChecksService, SubmissionConflict


def submission_checks_router(sessions=None, storage_root=None, template_storage_root=None):
    router = APIRouter(prefix='/cases/{case_id}/submission-checks', tags=['submission checks'])

    def run(case_id, operation):
        if sessions is None or storage_root is None or template_storage_root is None:
            raise HTTPException(503, 'Submission check persistence/storage is not configured')
        with sessions() as session:
            try:
                session.connection().exec_driver_sql('BEGIN IMMEDIATE')
                repo = Repository(session)
                try:
                    repo.get(s.Case, case_id)
                except ValueError:
                    raise HTTPException(404, 'Case not found')
                result = operation(SubmissionChecksService(repo, storage_root, template_storage_root))
                session.commit()
                return result
            except SubmissionConflict as error:
                raise HTTPException(409, dict(message=str(error), report=error.report)) from error
            except (WorkflowConflict, ContentIntegrityError, TemplateIntegrityError) as error:
                raise HTTPException(409, str(error)) from error
            except ValueError as error:
                raise HTTPException(422, str(error)) from error

    @router.get('/preview')
    def preview(case_id: str):
        return run(case_id, lambda service: service.preview(case_id))

    @router.post('')
    def record(case_id: str, request: CheckRequest):
        return run(case_id, lambda service: service.record(case_id, request))

    @router.post('/validate')
    def validate(case_id: str, request: CheckRequest):
        return run(case_id, lambda service: service.record(case_id, request, require_passed=True))

    @router.get('')
    def history(case_id: str):
        return run(case_id, lambda service: sorted(service.repo.list_for_case(s.SubmissionCheck, case_id),
                                                  key=lambda c: (c.created_at, c.id)))

    @router.get('/{check_id}')
    def get(case_id: str, check_id: str):
        return run(case_id, lambda service: service.get(case_id, check_id))

    return router
