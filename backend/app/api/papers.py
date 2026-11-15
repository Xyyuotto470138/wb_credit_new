"""Start a new paper from a borrower name, a paper type and a lending type."""
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .. import schemas as s
from ..es2.spec import lending_type, lending_types
from ..repository import Repository
from ..services.templates import TemplateRegistry
from ..team_config import load_team

ROOT = Path(__file__).resolve().parents[3]
NEW_PAPER_TEAM = 'fig_re'  # the only team set up in this build: the FIG Executive Summary specification
NEW_PAPER_MODEL = 'fable-5-2-direct'  # the drafting model of that specification (config/models.yaml); the mock model cannot draft it


class NewPaper(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    borrower_name: str = Field(min_length=1, max_length=200)
    case_type: Literal['new', 'renewal']  # shown as "New to bank" and "Annual review"
    lending_type: str = Field(min_length=1, max_length=100)  # an id from config/lending_types.yaml


# The form asks only for the borrower and the paper type. The other case facts take the values of a typical FIG REIT
# paper (the same as both demo papers), so the checklist asks for the full set of documents for that paper type.
STANDARD_FACTS = dict(borrower_type='reit', facility_types=['term', 'revolving'], property_or_asset_security=True,
    insured_security_or_assets=True, financial_covenants=True, covenants=True, new_money=True, property_income_repayment=True,
    bureau_covered=False, has_information_memorandum=False)


class DeletePaper(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    actor: str = Field(min_length=1, max_length=200)


def papers_router(sessions=None, template_storage_root=None, demo_case_ids=()):
    router = APIRouter(tags=['papers'])

    @router.get('/lending-types')
    def types():
        return [dict(id=t['id'], label=t['label'], focus=' '.join(t['focus'].split())) for t in lending_types()]

    @router.post('/papers', status_code=201)
    def create(body: NewPaper):
        if sessions is None:
            raise HTTPException(503, 'Case persistence is not configured')
        if not lending_type(body.lending_type):
            raise HTTPException(422, 'Choose a lending type from the list.')
        config = load_team(NEW_PAPER_TEAM)
        try:
            case = s.Case(team_id=NEW_PAPER_TEAM, config_version=config.template.version, config_hash=config.content_hash,
                existing_client=body.case_type == 'renewal', new_to_bank=body.case_type == 'new', default_model_id=NEW_PAPER_MODEL, **STANDARD_FACTS, **body.model_dump())
        except ValidationError as error:
            raise HTTPException(422, '; '.join(e['msg'].removeprefix('Value error, ') for e in error.errors()))
        with sessions() as session:
            session.connection().exec_driver_sql('BEGIN IMMEDIATE')
            repo = Repository(session)
            saved = repo.save(case)
            if template_storage_root is not None:  # the paper needs its team's Word template; a no-op when already loaded
                TemplateRegistry(repo, template_storage_root).seed_owner_templates(NEW_PAPER_TEAM, ROOT)
            session.commit()
            return dict(id=saved.id, borrower_name=saved.borrower_name, case_type=saved.case_type, team_id=saved.team_id, lending_type=saved.lending_type)

    @router.post('/papers/{case_id}/delete')
    def delete(case_id: str, body: DeletePaper):
        """Take a paper out of every list. Its files, drafts and trail stay in the store; nothing is erased."""
        if sessions is None:
            raise HTTPException(503, 'Case persistence is not configured')
        with sessions() as session:
            session.connection().exec_driver_sql('BEGIN IMMEDIATE')
            repo = Repository(session)
            try:
                case = repo.get(s.Case, case_id)
            except ValueError:
                raise HTTPException(404, 'Paper not found')
            if case.deleted_at:
                raise HTTPException(404, 'Paper not found')
            if case_id in demo_case_ids:
                raise HTTPException(409, 'The demo papers that come with the project cannot be deleted.')
            if case.workflow_state != 'Draft':
                raise HTTPException(409, 'Only a paper that is still being drafted can be deleted. This one has been submitted for review.')
            case.deleted_at, case.deleted_by = s.utcnow(), body.actor
            repo.save(case)
            session.commit()
            return dict(id=case.id, deleted=True)

    return router
