"""Template registry, comparison and IT export. Admin activation remains B23."""
from fastapi import APIRouter, HTTPException, Request, Response

from ..repository import Repository
from ..services.intake import MAX_BYTES
from ..services.templates import TemplateRegistry, TemplateNotFound, TemplateIntegrityError
from ..services.template_diff import it_change_list


def templates_router(sessions=None, storage_root=None):
    router = APIRouter(prefix='/templates/{team_id}', tags=['templates'])

    def run(team_id, operation, *, write=False):
        if sessions is None or storage_root is None:
            raise HTTPException(503, 'Template persistence is not configured')
        with sessions() as session:
            try:
                if write:
                    session.connection().exec_driver_sql('BEGIN IMMEDIATE')
                result = operation(TemplateRegistry(Repository(session), storage_root))
                session.commit()
                return result
            except TemplateNotFound as error:
                raise HTTPException(404, str(error)) from error
            except TemplateIntegrityError as error:
                raise HTTPException(409, str(error)) from error
            except ValueError as error:
                raise HTTPException(422, str(error)) from error

    @router.get('')
    def versions(team_id: str):
        return run(team_id, lambda registry: registry.versions(team_id))

    @router.get('/active')
    def active(team_id: str):
        return run(team_id, lambda registry: registry.active(team_id))

    @router.get('/{version_id}')
    def version(team_id: str, version_id: str):
        return run(team_id, lambda registry: registry.get(team_id, version_id))

    @router.get('/{version_id}/source')
    def source(team_id: str, version_id: str):
        content = run(team_id, lambda registry: registry.content(team_id, version_id))
        return Response(content, media_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                        headers={'Content-Disposition': 'attachment; filename="es-template.docx"'})

    @router.post('')
    async def register(team_id: str, request: Request, display_version: str, filename: str, parent_id: str | None = None):
        content = bytearray()
        async for chunk in request.stream():
            content.extend(chunk)
            if len(content) > MAX_BYTES:
                raise HTTPException(413, 'Template exceeds byte limit')
        return run(team_id, lambda registry: registry.register(team_id, display_version, filename,
                   bytes(content), parent_id), write=True)

    @router.post('/{version_id}/compare')
    def compare(team_id: str, version_id: str, expected_active_id: str | None = None):
        return run(team_id, lambda registry: registry.compare(team_id, version_id, expected_active_id), write=True)

    @router.get('/{version_id}/comparisons/{comparison_id}')
    def comparison(team_id: str, version_id: str, comparison_id: str):
        return run(team_id, lambda registry: registry.comparison(team_id, version_id, comparison_id))

    @router.get('/{version_id}/comparisons/{comparison_id}/it-change-list')
    def export_changes(team_id: str, version_id: str, comparison_id: str):
        content = run(team_id, lambda registry: it_change_list(registry.comparison(team_id, version_id, comparison_id)))
        return Response(content, media_type='text/plain; charset=utf-8',
                        headers={'Content-Disposition': 'attachment; filename="template-it-changes.txt"'})

    return router
