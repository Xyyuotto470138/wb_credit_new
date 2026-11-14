"""Serialized proposal creation and explicit CA decisions."""
from fastapi import APIRouter, HTTPException

from .. import schemas as s
from ..repository import Repository
from ..llm import client as llm
from ..retrieval.service import ContentIntegrityError
from ..services.templates import TemplateIntegrityError
from ..services.versions import RevisionConflict
from ..services.section_chat import SectionChatService, ChatRequest, Decision
from ..team_config import TeamConfig


def chat_router(sessions=None, storage_root=None, template_storage_root=None, provider=None):
    router = APIRouter(prefix='/cases/{case_id}/sections/{section_id}/chat', tags=['section chat'])

    def run(case_id, operation):
        if sessions is None or storage_root is None:
            raise HTTPException(503, 'Chat persistence is not configured')
        with sessions() as session:
            try:
                session.connection().exec_driver_sql('BEGIN IMMEDIATE')
                repo = Repository(session)
                repo.get(s.Case, case_id)
                result = operation(SectionChatService(repo, storage_root, template_storage_root, provider))
                session.commit()
                return result
            except (RevisionConflict, ContentIntegrityError, TemplateIntegrityError) as error:
                raise HTTPException(409, str(error)) from error
            except (ValueError, llm.LiveProviderDisabled) as error:
                raise HTTPException(422, str(error)) from error

    @router.get('')
    def history(case_id: str, section_id: int):
        return run(case_id, lambda service: service.history(case_id, section_id))

    @router.get('/metrics')
    def metrics(case_id: str, section_id: int):
        def selected(service):
            config = TeamConfig.model_validate(service.repo.get(s.Case, case_id).config_snapshot)
            return config.analytics.sets['reit'].metrics if section_id == 10 and 'reit' in config.analytics.sets else []
        return run(case_id, selected)

    @router.post('')
    def propose(case_id: str, section_id: int, request: ChatRequest):
        return run(case_id, lambda service: service.propose(case_id, section_id, request))

    @router.post('/{proposal_id}/decision')
    def decide(case_id: str, section_id: int, proposal_id: str, request: Decision):
        return run(case_id, lambda service: service.decide(case_id, section_id, proposal_id, request))

    return router
