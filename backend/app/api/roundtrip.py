"""Offline round trip: compare an ES edited in Word with the sections as they stand, and take chosen wording back."""
from fastapi import APIRouter, HTTPException, Request

from .. import schemas as s
from ..es2 import roundtrip
from ..repository import Repository
from ..retrieval.service import ContentIntegrityError
from ..services.locks import WorkflowConflict
from ..services.templates import TemplateIntegrityError
from ..services.versions import RevisionConflict, VersionService


def roundtrip_router(sessions=None, storage_root=None, template_storage_root=None):
    router = APIRouter(prefix='/cases/{case_id}/roundtrip', tags=['offline round trip'])

    def run(case_id, operation):
        if sessions is None or storage_root is None:
            raise HTTPException(503, 'Section persistence is not configured')
        with sessions() as session:
            try:
                session.connection().exec_driver_sql('BEGIN IMMEDIATE')
                repo = Repository(session)
                try:
                    repo.get(s.Case, case_id)
                except ValueError:
                    raise HTTPException(404, 'Case not found')
                result = operation(VersionService(repo, storage_root, template_storage_root))
                session.commit()
                return result
            except (RevisionConflict, ContentIntegrityError, TemplateIntegrityError, WorkflowConflict) as error:
                raise HTTPException(409, str(error)) from error
            except ValueError as error:
                raise HTTPException(422, str(error)) from error

    @router.post('/compare')
    async def compare(case_id: str, request: Request):
        """What an ES exported to Word and edited there changes, section by section. Nothing is saved."""
        content = bytearray()
        async for chunk in request.stream():
            if len(content) + len(chunk) > roundtrip.MAX_BYTES:
                raise HTTPException(413, 'The file is larger than 30 MB')
            content.extend(chunk)
        return run(case_id, lambda service: roundtrip.compare(service, case_id, bytes(content)))

    @router.post('/apply')
    def apply(case_id: str, request: roundtrip.ApplyRequest):
        """Save the wording the analyst chose from the edited file, and bring chosen Word comments in as review threads."""
        return run(case_id, lambda service: roundtrip.apply(service, case_id, request))

    return router
