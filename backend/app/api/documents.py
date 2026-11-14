"""Raw-byte uploads avoid adding a multipart dependency to the approved stack."""
import json
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from ..services.locks import WorkflowConflict
from .. import schemas
from ..repository import Repository
from ..services.intake import IntakeError, IntakeService, MAX_BYTES, Metadata


class ScanRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    folder_id: str = Field(min_length=1)
    metadata_by_path: dict[str, Metadata] = Field(default_factory=dict)


def documents_router(sessions=None, storage_root=None, folders=None):
    router = APIRouter(prefix='/cases/{case_id}/documents', tags=['documents'])

    def run(case_id, operation, *, write=False):
        if sessions is None or storage_root is None:
            raise HTTPException(503, 'Document persistence is not configured')
        with sessions() as session:
            try:
                if write:
                    # All API intake writers serialize duplicate/revision selection.
                    session.connection().exec_driver_sql('BEGIN IMMEDIATE')
                repository = Repository(session)
                try:
                    repository.get(schemas.Case, case_id)
                except ValueError:
                    raise HTTPException(404, 'Case not found')
                result = operation(IntakeService(repository, Path(storage_root), folders))
                session.commit()
                return result
            except WorkflowConflict as error:
                raise HTTPException(409, str(error)) from error
            except IntakeError as error:
                session.rollback()
                raise HTTPException(422, str(error)) from error
            except ValueError as error:
                session.rollback()
                raise HTTPException(422, 'Invalid document metadata or reference') from error

    @router.post('')
    async def upload(case_id: str, request: Request, filename: str, metadata: str = '{}'):
        try:
            hints = Metadata.model_validate(json.loads(metadata))
        except (ValueError, ValidationError) as error:
            raise HTTPException(422, 'Invalid classification metadata') from error
        content = bytearray()
        async for chunk in request.stream():
            if len(content) + len(chunk) > MAX_BYTES:
                raise HTTPException(413, 'File exceeds the intake byte limit')
            content.extend(chunk)
        return run(case_id, lambda service: service.ingest(case_id, filename, bytes(content), metadata=hints), write=True)

    @router.get('')
    def documents(case_id: str):
        return run(case_id, lambda service: service.repository.list_for_case(schemas.Document, case_id))

    @router.post('/scan')
    def scan(case_id: str, request: ScanRequest):
        return run(case_id, lambda service: service.scan(case_id, request.folder_id, request.metadata_by_path), write=True)

    return router
