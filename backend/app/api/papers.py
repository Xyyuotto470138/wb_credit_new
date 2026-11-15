"""Start a new paper from a borrower name and a paper type."""
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
    case_type: Literal['new', 'renewal']  # shown as "New to bank" and "Annual review"


# The form asks only for the borrower and the paper type. The other case facts take the values of a typical FIG REIT
# paper (the same as both demo papers), so the checklist asks for the full set of documents for that paper type.
STANDARD_FACTS = dict(borrower_type='reit', facility_types=['term', 'revolving'], property_or_asset_security=True,
    insured_security_or_assets=True, financial_covenants=True, covenants=True, new_money=True, property_income_repayment=True,
    bureau_covered=False, has_information_memorandum=False)


def papers_router(sessions=None, template_storage_root=None):
    router = APIRouter(tags=['papers'])

    @router.post('/papers', status_code=201)
    def create(body: NewPaper):
        if sessions is None:
            raise HTTPException(503, 'Case persistence is not configured')
        config = load_team(NEW_PAPER_TEAM)
        try:
            case = s.Case(team_id=NEW_PAPER_TEAM, config_version=config.template.version, config_hash=config.content_hash,
                existing_client=body.case_type == 'renewal', new_to_bank=body.case_type == 'new', **STANDARD_FACTS, **body.model_dump())
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
