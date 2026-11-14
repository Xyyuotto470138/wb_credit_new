"""Draft-only template exports with reviewable manifests and pinned requests."""
from io import BytesIO
import json
from zipfile import ZipFile, ZIP_DEFLATED

from fastapi import APIRouter, HTTPException, Response

from .. import schemas as s
from ..repository import Repository
from ..exports import ExportService, ExportRequest, ExportConflict
from ..retrieval.service import ContentIntegrityError
from ..services.templates import TemplateIntegrityError

DOCX='application/vnd.openxmlformats-officedocument.wordprocessingml.document'


def exports_router(sessions=None,storage_root=None,template_storage_root=None,export_storage_root=None):
    router=APIRouter(prefix='/cases/{case_id}/exports',tags=['draft exports'])

    def run(case_id,operation,write=False):
        if sessions is None or storage_root is None or template_storage_root is None:
            raise HTTPException(503,'Export persistence/template storage is not configured')
        with sessions() as session:
            try:
                if write: session.connection().exec_driver_sql('BEGIN IMMEDIATE')
                repo=Repository(session)
                try: repo.get(s.Case,case_id)
                except ValueError: raise HTTPException(404,'Case not found')
                result=operation(ExportService(repo,storage_root,template_storage_root,export_storage_root))
                session.commit(); return result
            except (ExportConflict,ContentIntegrityError,TemplateIntegrityError) as error:
                raise HTTPException(409,str(error)) from error
            except ValueError as error:
                raise HTTPException(422,str(error)) from error

    @router.get('/preview')
    def preview(case_id:str):
        return run(case_id,lambda service:service.prepare(case_id)[0],True)

    @router.post('')
    def create(case_id:str,request:ExportRequest):
        return run(case_id,lambda service:service.create(case_id,request),True)

    @router.get('')
    def listing(case_id:str):
        return run(case_id,lambda service:[dict(id=a.id,es_version_id=a.es_version_id,created_at=a.created_at,
            content_hash=a.content_hash,status=a.manifest['status'],template=a.manifest['template'])
            for a in service.repo.list_for_case(s.ExportArtifact,case_id)])

    @router.get('/{artifact_id}/manifest')
    def manifest(case_id:str,artifact_id:str):
        return run(case_id,lambda service:service.get(case_id,artifact_id).manifest)

    @router.get('/{artifact_id}/document.docx')
    def document(case_id:str,artifact_id:str):
        data=run(case_id,lambda service:service.content(case_id,artifact_id))
        return Response(data,media_type=DOCX,headers={'Content-Disposition':'attachment; filename="wb-credit-draft.docx"'})

    @router.get('/{artifact_id}/request-list.txt')
    def requests(case_id:str,artifact_id:str):
        text=run(case_id,lambda service:service.get(case_id,artifact_id).manifest['request_list'])
        return Response(text,media_type='text/plain',headers={'Content-Disposition':'attachment; filename="wb-credit-requests.txt"'})

    @router.get('/{artifact_id}/bundle.zip')
    def bundle(case_id:str,artifact_id:str):
        def operation(service):
            artifact=service.get(case_id,artifact_id)
            output=BytesIO()
            with ZipFile(output,'w',ZIP_DEFLATED) as archive:
                archive.writestr('draft.docx',service.content(case_id,artifact_id))
                archive.writestr('manifest.json',json.dumps(artifact.manifest,ensure_ascii=False,indent=2))
                archive.writestr('request-list.txt',artifact.manifest['request_list'])
            return output.getvalue()
        return Response(run(case_id,operation),media_type='application/zip',headers={'Content-Disposition':'attachment; filename="wb-credit-draft-bundle.zip"'})

    return router
