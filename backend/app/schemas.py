"""Validated persistence contracts. Versioned facts are separate from mutable pointers."""
from datetime import datetime, timezone
from decimal import Decimal
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

DocumentStatus = Literal['Provided', 'Found publicly', 'Can generate', 'Missing', 'Suggested', 'Not applicable', 'Dismissed']
Readiness = Literal['Waiting for input', 'Can draft (partial)', 'Can draft (full)', 'Not applicable', 'Drafted', 'Stale', 'CA confirmed']
WorkflowState = Literal['Draft', 'Submitted to Credit Head', 'Supported', 'With Credit Approver', 'Returned to CA', 'Question to CA', 'Approved', 'Approved with conditions', 'Declined']
Role = Literal['CA', 'Credit Head', 'Credit Approver', 'template admin', 'credit admin support']


def utcnow():
    return datetime.now(timezone.utc)


class Record(BaseModel):
    model_config = ConfigDict(extra='forbid', validate_assignment=True)
    id: str = Field(default_factory=lambda: str(uuid4()), min_length=1)
    created_at: datetime = Field(default_factory=utcnow)

    @model_validator(mode='after')
    def utc_timestamps(self):
        for name in type(self).model_fields:
            value = getattr(self, name)
            if isinstance(value, datetime) and (value.tzinfo is None or value.utcoffset().total_seconds() != 0):
                raise ValueError(f'{name} must be UTC with timezone')
        return self


class Case(Record):
    borrower_name: str = Field(min_length=1)
    public_identifiers: dict[str, str] = Field(default_factory=dict)
    team_id: str
    config_version: str
    config_hash: str
    config_snapshot: dict = Field(default_factory=dict)
    case_type: Literal['new', 'renewal']
    borrower_type: str
    facility_types: list[str] = Field(default_factory=list)
    existing_client: bool
    new_to_bank: bool
    property_or_asset_security: bool = False
    insured_security_or_assets: bool = False
    financial_covenants: bool = False
    covenants: bool = False
    new_money: bool = False
    property_income_repayment: bool = False
    bureau_covered: bool = False
    has_information_memorandum: bool = False
    public_entity: bool = False
    ca_position: str | None = None
    lending_type: str | None = None  # an id from config/lending_types.yaml; papers started before it existed have none
    default_model_id: str = 'mock-v1'
    workflow_state: WorkflowState = 'Draft'
    active_es_version_id: str | None = None
    first_upload_at: datetime | None = None
    deleted_at: datetime | None = None  # set when the maker deletes the paper: it leaves every list, its records stay in the store
    deleted_by: str | None = None

    @model_validator(mode='after')
    def client_distinction(self):
        if self.existing_client == self.new_to_bank:
            raise ValueError('Set exactly one of existing_client and new_to_bank')
        if self.case_type == 'renewal' and not self.existing_client:
            raise ValueError('Renewal requires an existing client')
        return self


class Owned(Record):
    case_id: str


class Document(Owned):
    catalogue_id: int | None = None
    suggestion_id: str | None = None
    entity: str
    period: str | None = None
    content_hash: str = Field(pattern=r'^[0-9a-f]{64}$')
    storage_path: str
    revision: int = Field(default=1, ge=1)
    supersedes_id: str | None = None
    origin: Literal['upload', 'folder', 'public', 'generated']
    synthetic: bool
    original_filename: str
    url: str | None = None
    retrieved_at: datetime | None = None
    confirmed_by: str | None = None
    confirmed_at: datetime | None = None
    conflict_status: Literal['none', 'pending', 'accepted', 'rejected'] = 'none'
    intake: dict = Field(default_factory=dict)

    @model_validator(mode='after')
    def provenance(self):
        if self.origin == 'public' and (not self.url or not self.url.startswith(('https://', 'http://')) or not self.retrieved_at):
            raise ValueError('Public documents require HTTP(S) URL and retrieval date')
        if bool(self.confirmed_by) != bool(self.confirmed_at):
            raise ValueError('Confirmation requires actor and time')
        return self


class ExpectedDocument(Owned):
    catalogue_id: int | None = None
    suggestion_id: str | None = None
    applicable: bool
    mandatory: bool
    reason: str
    alternative_group: str | None = None
    usual_owner: str
    section_ids: list[int]
    status: DocumentStatus
    document_ids: list[str] = Field(default_factory=list)
    search_outcome: Literal['not run', 'failed', 'no match', 'found'] = 'not run'
    search_attempts: list[dict] = Field(default_factory=list)
    generated_offer: str | None = None
    dismiss_reason: str | None = None
    confirmed_by: str | None = None

    @model_validator(mode='after')
    def identity_and_dismissal(self):
        if (self.catalogue_id is None) == (self.suggestion_id is None):
            raise ValueError('Expected item needs exactly one catalogue or suggestion ID')
        if self.status == 'Dismissed' and (not self.dismiss_reason or not self.dismiss_reason.strip() or not self.confirmed_by):
            raise ValueError('Dismissal needs a reason and confirmer; it is not a submission override')
        return self


class Section(Owned):
    section_id: int = Field(ge=1)
    applicable: bool = True
    na_reason: str | None = None
    readiness: Readiness = 'Waiting for input'
    completeness: Literal['none', 'partial', 'full'] = 'none'
    gaps: list[str] = Field(default_factory=list)
    current_draft_id: str | None = None
    confirmed_draft_id: str | None = None
    input_fingerprint: str = ''
    editor_revision: int = Field(default=0, ge=0)

    @model_validator(mode='after')
    def na(self):
        if (not self.applicable or self.readiness == 'Not applicable') and not (self.na_reason and self.na_reason.strip()):
            raise ValueError('Not applicable requires a reason')
        if self.readiness == 'CA confirmed' and (not self.current_draft_id or self.confirmed_draft_id != self.current_draft_id):
            raise ValueError('Confirmation must name the current draft')
        return self


class SectionConfirmation(Owned):
    section_id: int
    draft_id: str
    input_fingerprint: str
    editor_revision: int = Field(ge=0)
    actor: str = Field(min_length=1, pattern=r'.*\S.*')
    role: Literal['CA'] = 'CA'


class TemplateVersion(Record):
    team_id: str
    display_version: str
    content_hash: str = Field(pattern=r'^[0-9a-f]{64}$')
    storage_path: str
    parent_id: str | None = None
    parsed_map: dict = Field(default_factory=dict)
    parse_gaps: list[str] = Field(default_factory=list)
    status: Literal['candidate', 'mapped', 'review required'] = 'candidate'


class TemplateActivation(Record):
    team_id: str
    template_version_id: str
    expected_previous_id: str | None = None
    actor: str
    role: Literal['template admin']


class TemplateChange(Record):
    template_version_id: str
    section_id: int | None = None
    anchor: str
    before: str
    after: str
    category: Literal['formatting', 'prompt', 'code']
    reason: str = Field(min_length=1)
    confirmed_by: str | None = None
    confirmed_at: datetime | None = None
    change_list_path: str | None = None


class TemplateComparison(Record):
    team_id: str
    template_version_id: str
    baseline_version_id: str
    report: dict


class DraftVersion(Owned):
    section_id: int
    parent_id: str | None = None
    text: str
    claim_spans: list[dict] = Field(default_factory=list)
    computed_value_ids: list[str] = Field(default_factory=list)
    document_ids: list[str] = Field(default_factory=list)
    ca_input_ids: list[str] = Field(default_factory=list)
    config_hash: str
    prompt_version: str
    model_version: str
    template_version_id: str
    input_fingerprint: str
    author: str
    ca_edits: bool = False
    gaps: list[str] = Field(default_factory=list)


class ESVersion(Owned):
    parent_id: str | None = None
    section_versions: dict[int, str]
    config_hash: str
    template_version_id: str
    author: str
    purpose: Literal['working', 'export', 'submission', 'approved', 'approved with conditions', 'declined']
    gap_reasons: dict[str, str] = Field(default_factory=dict)


class ChatMessage(Owned):
    section_id: int
    base_draft_id: str
    actor: str
    text: str = Field(min_length=1)


class CAInput(Owned):
    message_id: str
    supersedes_id: str | None = None
    revision: int = Field(default=1, ge=1)
    actor: str
    fact: str
    numeric_input: dict | None = None


class Evidence(Owned):
    document_id: str | None = None
    ca_input_id: str | None = None
    page: int | None = Field(default=None, ge=1)
    printed_page: str | None = None
    region: str | None = None
    excerpt: str
    origin: Literal['upload', 'folder', 'public', 'generated', 'CA input']
    synthetic: bool
    url: str | None = None
    retrieved_at: datetime | None = None

    @model_validator(mode='after')
    def source(self):
        if (self.document_id is None) == (self.ca_input_id is None):
            raise ValueError('Evidence needs exactly one document or CA input')
        if self.document_id and (self.page is None or self.origin == 'CA input'):
            raise ValueError('Document evidence requires a page and document origin')
        if self.ca_input_id and self.origin != 'CA input':
            raise ValueError('Typed facts must be labelled CA input')
        if self.origin == 'public' and (not self.url or not self.retrieved_at):
            raise ValueError('Public evidence needs URL and retrieval date')
        return self


class EvidenceIndex(Owned):
    document_id: str
    normalizer_version: str
    evidence_ids: list[str]
    locators: dict[str, dict]
    gaps: list[str]


class Citation(Owned):
    evidence_id: str
    draft_id: str | None = None
    computed_value_id: str | None = None
    claim_or_cell: str

    @model_validator(mode='after')
    def target(self):
        if (self.draft_id is None) == (self.computed_value_id is None):
            raise ValueError('Citation needs exactly one claim or computed-value target')
        return self


class Spread(Owned):
    document_ids: list[str]
    ca_input_ids: list[str] = Field(default_factory=list)
    version: str
    values: dict
    validation_status: Literal['pending', 'valid', 'invalid', 'manual review']
    issues: list[str] = Field(default_factory=list)


class ComputedValue(Owned):
    spread_id: str | None = None
    metric: str
    formula_version: str
    operands: dict[str, Decimal]
    operand_evidence_ids: dict[str, list[str]]
    unit: str
    currency: str | None = None
    period: str
    scope: str
    value: Decimal | None
    validated: bool = False
    proxy: bool = False
    synthetic: bool
    gaps: list[str] = Field(default_factory=list)

    @model_validator(mode='after')
    def sourced_operands(self):
        if set(self.operands) != set(self.operand_evidence_ids) or any(not refs for refs in self.operand_evidence_ids.values()):
            raise ValueError('Each operand requires evidence')
        if self.value is None and not self.gaps:
            raise ValueError('Unknown value requires a gap')
        return self


class SectionProposal(Owned):
    payload: dict = Field(default_factory=dict)
    message_id: str
    section_id: int
    base_draft_id: str
    proposed_text: str
    evidence_ids: list[str]
    computed_value_ids: list[str] = Field(default_factory=list)
    model_version: str
    status: Literal['pending', 'accepted', 'rejected', 'stale'] = 'pending'
    resolved_by: str | None = None
    resolved_at: datetime | None = None
    accepted_draft_id: str | None = None


class WorkflowEvent(Owned):
    action: str
    actor: str
    role: Role
    from_state: WorkflowState
    to_state: WorkflowState
    es_version_id: str
    returned_sections: list[int] = Field(default_factory=list)
    override_reason: str | None = None
    payload: dict = Field(default_factory=dict)


class Comment(Owned):
    section_id: int | None = None
    draft_id: str | None = None
    es_version_id: str | None = None
    author: str
    role: Role
    body: str = Field(min_length=1)
    parent_id: str | None = None
    resolved_at: datetime | None = None

    @model_validator(mode='after')
    def version_bound(self):
        if not self.draft_id and not self.es_version_id:
            raise ValueError('Comment must be version-bound')
        return self


class SubmissionCheck(Owned):
    es_version_id: str
    section_results: dict[int, dict]
    mandatory_gap_reasons: dict[str, str]
    freshness_results: dict[int, bool]
    passed: bool
    checked_by: str
    report: dict = Field(default_factory=dict)


class ApproverQuestion(Owned):
    es_version_id: str
    section_ids: list[int]
    question: str = Field(min_length=1)
    asked_by: str
    answer: str | None = None
    answered_by: str | None = None
    answered_at: datetime | None = None
    resubmitted_es_version_id: str | None = None

    @model_validator(mode='after')
    def answer_record(self):
        if self.answer is not None and (not self.answer.strip() or not self.answered_by or not self.answered_at):
            raise ValueError('Answer requires text, actor and time')
        if self.resubmitted_es_version_id and not self.answer:
            raise ValueError('Question resubmission requires an answer')
        return self


class SenseCheck(Owned):
    """A model's reasonableness read of the tables that code does not check. Suggestions for a human check, never a pass."""
    section_id: int
    draft_id: str
    findings: list[dict] = Field(default_factory=list)
    tables_checked: int = 0
    model: str
    cost_usd: str | None = None
    checked_by: str
    resolutions: dict[str, dict] = Field(default_factory=dict)


class ReviewMark(Owned):
    """A checker's mark on one section of a submitted ES: reviewed, or a query for the maker. Append-only; the latest counts."""
    section_id: int
    draft_id: str
    es_version_id: str
    reviewer: str
    role: Role
    status: Literal['reviewed', 'query', 'cleared']
    note: str = ''


class UpdateProposal(Owned):
    """A proposed update of one drafted section after documents changed. Nothing in it reaches the section until the maker applies it."""
    section_id: int
    base_draft_id: str
    input_fingerprint: str
    documents_key: str
    candidate: dict
    changes: list[dict] = Field(default_factory=list)
    kept: list[str] = Field(default_factory=list)
    proposed_by: str
    cost_usd: str | None = None
    status: Literal['pending', 'applied', 'dismissed', 'superseded'] = 'pending'
    decisions: dict = Field(default_factory=dict)
    resolved_by: str | None = None
    resolved_at: datetime | None = None
    applied_draft_id: str | None = None


class ExportArtifact(Owned):
    es_version_id: str
    content_hash: str = Field(pattern=r'^[0-9a-f]{64}$')
    manifest: dict
