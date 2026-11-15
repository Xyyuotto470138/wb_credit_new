"""Start a new paper. The facts given here decide which documents and sections apply to it."""
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .. import schemas as s
from ..repository import Repository
from ..services.templates import TemplateRegistry
from ..team_config import load_team

ROOT = Path(__file__).resolve().parents[3]
NEW_PAPER_TEAM = 'fig_re'  # the only team set up in this build: the FIG Executive Summary specification


class NewPaper(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    borrower_name: str = Field(min_length=1, max_length=200)
    case_type: Literal['new', 'renewal']
    existing_client: bool
    borrower_type: Literal['reit', 'fund', 'bank', 'other'] = 'reit'
    facility_types: list[Literal['term', 'revolving', 'acquisition']] = Field(default_factory=list)
    property_or_asset_security: bool = False
    insured_security_or_assets: bool = False
    financial_covenants: bool = False
    covenants: bool = False
    new_money: bool = False
    property_income_repayment: bool = False
    bureau_covered: bool = False
    has_information_memorandum: bool = False


def papers_router(sessions=None, template_storage_root=None):
    router = APIRouter(tags=['papers'])

    @router.post('/papers', status_code=201)
    def create(body: NewPaper):
        if sessions is None:
            raise HTTPException(503, 'Case persistence is not configured')
        config = load_team(NEW_PAPER_TEAM)
        try:
            case = s.Case(team_id=NEW_PAPER_TEAM, config_version=config.template.version, config_hash=config.content_hash,
                new_to_bank=not body.existing_client, **body.model_dump())
        except ValidationError as error:
            raise HTTPException(422, '; '.join(e['msg'].removeprefix('Value error, ') for e in error.errors()))
        with sessions() as session:
            session.connection().exec_driver_sql('BEGIN IMMEDIATE')
            repo = Repository(session)
            saved = repo.save(case)
            if template_storage_root is not None:  # the paper needs its team's Word template; a no-op when already loaded
                TemplateRegistry(repo, template_storage_root).seed_owner_templates(NEW_PAPER_TEAM, ROOT)
            session.commit()
            return dict(id=saved.id, borrower_name=saved.borrower_name, case_type=saved.case_type, team_id=saved.team_id)

    return router
