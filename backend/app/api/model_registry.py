"""B26 registry, CA case preference and ephemeral comparison endpoints."""
from fastapi import APIRouter, HTTPException

from ..llm import client
from ..llm import live
from ..llm.registry import load_registry, LIVE_BLOCK
from ..repository import Repository
from ..retrieval.service import ContentIntegrityError
from ..services.templates import TemplateIntegrityError
from ..services.versions import RevisionConflict
from ..services.model_comparison import DefaultModelRequest, CompareRequest, set_default, compare


def models_router(sessions=None, storage_root=None, template_storage_root=None):
    router = APIRouter(tags=['model selection'])

    @router.get('/models')
    def listing():
        registry = load_registry()
        return dict(version=registry.version, default_model=registry.default_model,
            live_calls_enabled=live.live_enabled(), live_block_reason=None if live.live_enabled() else LIVE_BLOCK,
            models=[m.public() for m in registry.models])

    @router.get('/costs')
    def costs():
        """Running totals of live calls by model, from the append-only ledger."""
        entries = live.read_ledger()
        return dict(totals=live.totals(entries), calls=len(entries), recent=entries[-20:])

    def run(operation):
        if sessions is None:
            raise HTTPException(503, 'Case persistence is not configured')
        with sessions() as session:
            try:
                session.connection().exec_driver_sql('BEGIN IMMEDIATE')
                result = operation(Repository(session))
                session.commit()
                return result
            except (RevisionConflict, ContentIntegrityError, TemplateIntegrityError) as error:
                raise HTTPException(409, str(error)) from error
            except (ValueError, client.LiveProviderDisabled) as error:
                raise HTTPException(422, str(error)) from error

    @router.post('/cases/{case_id}/model')
    def choose(case_id: str, request: DefaultModelRequest):
        return run(lambda repo: set_default(repo, case_id, request).model_dump(mode='json', exclude={'config_snapshot'}))

    @router.post('/cases/{case_id}/sections/{section_id}/compare')
    def comparison(case_id: str, section_id: int, request: CompareRequest):
        if storage_root is None or template_storage_root is None:
            raise HTTPException(503, 'Draft storage is not configured')
        return run(lambda repo: compare(repo, storage_root, template_storage_root, case_id, section_id, request))

    return router
