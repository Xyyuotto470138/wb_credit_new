"""Endpoints for the specification-driven ES: the layout for the screen, saved images, and the model sense check."""
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from .. import schemas as s
from ..repository import Repository
from ..llm.client import LiveProviderDisabled
from . import sense
from .blocks import image_path
from .compute import ROOT, case_assets
from .spec import load_spec


def es2_router(sessions=None, storage_root=None):
    router = APIRouter(tags=['ES specification'])
    router.live_client = None  # tests inject a stub here; live runs build the real client from the registry entry

    def case(case_id):
        if sessions is None:
            raise HTTPException(503, 'Case persistence is not configured')
        with sessions() as session:
            try:
                return Repository(session).get(s.Case, case_id)
            except ValueError as error:
                raise HTTPException(404, 'Case not found') from error

    @router.get('/cases/{case_id}/es-spec')
    def spec(case_id: str):
        """The section layout for this case's team, or null for teams on the first-generation path."""
        found = load_spec(case(case_id).team_id)
        if not found:
            return None
        keep = ('key', 'type', 'title', 'guidance', 'fill', 'options', 'questions', 'slots', 'only_when')
        return dict(version=found['version'], team_label=found.get('team_label'), sections=[
            dict(id=section['id'], parts=[{k: part[k] for k in keep if k in part} for part in section['parts'] if not part.get('hidden')])
            for section in found['sections']])

    @router.get('/cases/{case_id}/assets')
    def asset(case_id: str, path: str):
        """A saved image declared for this case (photograph or map). Only declared files are served."""
        assets = case_assets(case(case_id).id)
        allowed = {item['file'] for item in assets.get('property_photos') or []} | ({assets['location_map']} if assets.get('location_map') else set())
        if path.startswith('generated/') and storage_root:  # a chart drawn by the system for this case
            folder = (Path(storage_root) / 'assets').resolve()
            target = (folder / Path(path).name).resolve()
            if target.parent != folder or not target.is_file():
                raise HTTPException(404, 'Asset not found')
            return FileResponse(target, media_type='image/png')
        if path not in allowed:
            raise HTTPException(404, 'Asset not found')
        target = (ROOT / path).resolve()
        if not target.is_relative_to(ROOT) or not target.is_file():
            raise HTTPException(404, 'Asset not found')
        return FileResponse(target, media_type='image/png' if Path(path).suffix == '.png' else 'image/jpeg')

    def write(case_id, operation):
        if sessions is None:
            raise HTTPException(503, 'Case persistence is not configured')
        with sessions() as session:
            try:
                session.connection().exec_driver_sql('BEGIN IMMEDIATE')
                repo = Repository(session)
                repo.get(s.Case, case_id)
                result = operation(repo)
                session.commit()
                return result
            except LiveProviderDisabled as error:
                raise HTTPException(422, str(error)) from error
            except ValueError as error:
                raise HTTPException(422, str(error)) from error

    @router.get('/cases/{case_id}/sense-checks')
    def sense_checks(case_id: str):
        """The latest model sense check of each section. Suggestions for a human check, never a pass."""
        return write(case_id, lambda repo: sense.listing(repo, case_id))

    @router.post('/cases/{case_id}/sections/{section_id}/sense-check')
    def sense_check(case_id: str, section_id: int, request: sense.SenseRequest):
        from types import SimpleNamespace
        write(case_id, lambda repo: sense.run(SimpleNamespace(repo=repo), case_id, section_id, request, client=router.live_client))
        return sense_checks(case_id)

    @router.post('/cases/{case_id}/sense-checks/{check_id}/resolve')
    def sense_resolve(case_id: str, check_id: str, request: sense.ResolveRequest):
        write(case_id, lambda repo: sense.resolve(repo, case_id, check_id, request))
        return sense_checks(case_id)

    @router.get('/cases/{case_id}/blocks/{name}')
    def block_image(case_id: str, name: str):
        """An image the analyst added to a section of this case."""
        try:
            target = image_path(storage_root, case(case_id).id, name)
        except (ValueError, TypeError) as error:
            raise HTTPException(404, 'Image not found') from error
        return FileResponse(target, media_type='image/png' if name.endswith('.png') else 'image/jpeg',
                            headers={'X-Content-Type-Options': 'nosniff', 'Cache-Control': 'private, max-age=3600'})

    return router
