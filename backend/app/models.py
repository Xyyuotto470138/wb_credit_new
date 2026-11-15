"""Relational storage for schemas.py; JSON is limited to structured collections.

Writes go through Repository validation. SQL foreign keys also protect scalar links.
"""
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.types import TypeDecorator
from sqlalchemy.orm import mapped_column

from .database import Base

class UTCDateTime(TypeDecorator):
    impl = String
    cache_ok = True

    def process_bind_param(self, value, dialect):
        return value.isoformat() if value is not None else None

    def process_result_value(self, value, dialect):
        return datetime.fromisoformat(value) if value is not None else None


class ExactDecimal(TypeDecorator):
    impl = String
    cache_ok = True

    def process_bind_param(self, value, dialect):
        return str(value) if value is not None else None

    def process_result_value(self, value, dialect):
        return Decimal(value) if value is not None else None


class Case(Base):
    __tablename__ = 'case'
    id = mapped_column(Text, primary_key=True)
    created_at = mapped_column(UTCDateTime, nullable=False)
    borrower_name = mapped_column(Text, nullable=False)
    public_identifiers = mapped_column(JSON, nullable=False)
    team_id = mapped_column(Text, nullable=False)
    config_version = mapped_column(Text, nullable=False)
    config_snapshot = mapped_column(JSON, nullable=False)
    config_hash = mapped_column(Text, nullable=False)
    case_type = mapped_column(Text, nullable=False)
    borrower_type = mapped_column(Text, nullable=False)
    facility_types = mapped_column(JSON, nullable=False)
    existing_client = mapped_column(Boolean, nullable=False)
    new_to_bank = mapped_column(Boolean, nullable=False)
    property_or_asset_security = mapped_column(Boolean, nullable=False)
    insured_security_or_assets = mapped_column(Boolean, nullable=False)
    financial_covenants = mapped_column(Boolean, nullable=False)
    covenants = mapped_column(Boolean, nullable=False)
    new_money = mapped_column(Boolean, nullable=False)
    property_income_repayment = mapped_column(Boolean, nullable=False)
    bureau_covered = mapped_column(Boolean, nullable=False)
    has_information_memorandum = mapped_column(Boolean, nullable=False)
    public_entity = mapped_column(Boolean, nullable=False)
    ca_position = mapped_column(Text, nullable=True)
    lending_type = mapped_column(Text, nullable=True)
    default_model_id = mapped_column(Text, nullable=False, default='mock-v1', server_default='mock-v1')
    workflow_state = mapped_column(Text, nullable=False)
    active_es_version_id = mapped_column(Text, ForeignKey("e_s_version.id"), nullable=True)
    first_upload_at = mapped_column(UTCDateTime, nullable=True)
    __table_args__ = (CheckConstraint("case_type IN ('new', 'renewal')"), CheckConstraint("workflow_state IN ('Draft', 'Submitted to Credit Head', 'Supported', 'With Credit Approver', 'Returned to CA', 'Question to CA', 'Approved', 'Approved with conditions', 'Declined')"), CheckConstraint("existing_client != new_to_bank"), CheckConstraint("case_type != 'renewal' OR existing_client = 1"),)

class Document(Base):
    __tablename__ = 'document'
    id = mapped_column(Text, primary_key=True)
    created_at = mapped_column(UTCDateTime, nullable=False)
    case_id = mapped_column(Text, ForeignKey("case.id"), nullable=False)
    catalogue_id = mapped_column(Integer, nullable=True)
    suggestion_id = mapped_column(Text, nullable=True)
    entity = mapped_column(Text, nullable=False)
    period = mapped_column(Text, nullable=True)
    content_hash = mapped_column(Text, nullable=False)
    storage_path = mapped_column(Text, nullable=False)
    revision = mapped_column(Integer, nullable=False)
    supersedes_id = mapped_column(Text, ForeignKey("document.id"), nullable=True)
    origin = mapped_column(Text, nullable=False)
    synthetic = mapped_column(Boolean, nullable=False)
    original_filename = mapped_column(Text, nullable=False)
    url = mapped_column(Text, nullable=True)
    retrieved_at = mapped_column(UTCDateTime, nullable=True)
    confirmed_by = mapped_column(Text, nullable=True)
    confirmed_at = mapped_column(UTCDateTime, nullable=True)
    conflict_status = mapped_column(Text, nullable=False)
    intake = mapped_column(JSON, nullable=False, default=dict)
    __table_args__ = (CheckConstraint("origin IN ('upload', 'folder', 'public', 'generated')"), CheckConstraint("conflict_status IN ('none', 'pending', 'accepted', 'rejected')"),)

class ExpectedDocument(Base):
    __tablename__ = 'expected_document'
    id = mapped_column(Text, primary_key=True)
    created_at = mapped_column(UTCDateTime, nullable=False)
    case_id = mapped_column(Text, ForeignKey("case.id"), nullable=False)
    catalogue_id = mapped_column(Integer, nullable=True)
    suggestion_id = mapped_column(Text, nullable=True)
    applicable = mapped_column(Boolean, nullable=False)
    mandatory = mapped_column(Boolean, nullable=False)
    reason = mapped_column(Text, nullable=False)
    alternative_group = mapped_column(Text, nullable=True)
    usual_owner = mapped_column(Text, nullable=False)
    section_ids = mapped_column(JSON, nullable=False)
    status = mapped_column(Text, nullable=False)
    document_ids = mapped_column(JSON, nullable=False)
    search_outcome = mapped_column(Text, nullable=False)
    search_attempts = mapped_column(JSON, nullable=False)
    generated_offer = mapped_column(Text, nullable=True)
    dismiss_reason = mapped_column(Text, nullable=True)
    confirmed_by = mapped_column(Text, nullable=True)
    __table_args__ = (CheckConstraint("status IN ('Provided', 'Found publicly', 'Can generate', 'Missing', 'Suggested', 'Not applicable', 'Dismissed')"), CheckConstraint("search_outcome IN ('not run', 'failed', 'no match', 'found')"),)

class Section(Base):
    __tablename__ = 'section'
    id = mapped_column(Text, primary_key=True)
    created_at = mapped_column(UTCDateTime, nullable=False)
    case_id = mapped_column(Text, ForeignKey("case.id"), nullable=False)
    section_id = mapped_column(Integer, nullable=False)
    applicable = mapped_column(Boolean, nullable=False)
    na_reason = mapped_column(Text, nullable=True)
    readiness = mapped_column(Text, nullable=False)
    completeness = mapped_column(Text, nullable=False)
    gaps = mapped_column(JSON, nullable=False)
    current_draft_id = mapped_column(Text, ForeignKey("draft_version.id"), nullable=True)
    confirmed_draft_id = mapped_column(Text, ForeignKey("draft_version.id"), nullable=True)
    input_fingerprint = mapped_column(Text, nullable=False)
    editor_revision = mapped_column(Integer, nullable=False)
    __table_args__ = (CheckConstraint("readiness IN ('Waiting for input', 'Can draft (partial)', 'Can draft (full)', 'Not applicable', 'Drafted', 'Stale', 'CA confirmed')"), CheckConstraint("completeness IN ('none', 'partial', 'full')"), UniqueConstraint("case_id", "section_id"),)

class SectionConfirmation(Base):
    __tablename__ = 'section_confirmation'
    id = mapped_column(Text, primary_key=True)
    created_at = mapped_column(UTCDateTime, nullable=False)
    case_id = mapped_column(Text, ForeignKey('case.id'), nullable=False)
    section_id = mapped_column(Integer, nullable=False)
    draft_id = mapped_column(Text, ForeignKey('draft_version.id'), nullable=False)
    input_fingerprint = mapped_column(Text, nullable=False)
    editor_revision = mapped_column(Integer, nullable=False)
    actor = mapped_column(Text, nullable=False)
    role = mapped_column(Text, nullable=False)


class TemplateVersion(Base):
    __tablename__ = 'template_version'
    id = mapped_column(Text, primary_key=True)
    created_at = mapped_column(UTCDateTime, nullable=False)
    team_id = mapped_column(Text, nullable=False)
    display_version = mapped_column(Text, nullable=False)
    content_hash = mapped_column(Text, nullable=False)
    storage_path = mapped_column(Text, nullable=False)
    parent_id = mapped_column(Text, ForeignKey("template_version.id"), nullable=True)
    parsed_map = mapped_column(JSON, nullable=False)
    parse_gaps = mapped_column(JSON, nullable=False)
    status = mapped_column(Text, nullable=False)
    __table_args__ = (CheckConstraint("status IN ('candidate', 'mapped', 'review required')"),)

class TemplateActivation(Base):
    __tablename__ = 'template_activation'
    id = mapped_column(Text, primary_key=True)
    created_at = mapped_column(UTCDateTime, nullable=False)
    team_id = mapped_column(Text, nullable=False)
    template_version_id = mapped_column(Text, ForeignKey("template_version.id"), nullable=False)
    expected_previous_id = mapped_column(Text, ForeignKey("template_version.id"), nullable=True)
    actor = mapped_column(Text, nullable=False)
    role = mapped_column(Text, nullable=False)
    __table_args__ = (CheckConstraint("role IN ('template admin')"),)

class TemplateChange(Base):
    __tablename__ = 'template_change'
    id = mapped_column(Text, primary_key=True)
    created_at = mapped_column(UTCDateTime, nullable=False)
    template_version_id = mapped_column(Text, ForeignKey("template_version.id"), nullable=False)
    section_id = mapped_column(Integer, nullable=True)
    anchor = mapped_column(Text, nullable=False)
    before = mapped_column(Text, nullable=False)
    after = mapped_column(Text, nullable=False)
    category = mapped_column(Text, nullable=False)
    reason = mapped_column(Text, nullable=False)
    confirmed_by = mapped_column(Text, nullable=True)
    confirmed_at = mapped_column(UTCDateTime, nullable=True)
    change_list_path = mapped_column(Text, nullable=True)
    __table_args__ = (CheckConstraint("category IN ('formatting', 'prompt', 'code')"),)

class DraftVersion(Base):
    __tablename__ = 'draft_version'
    id = mapped_column(Text, primary_key=True)
    created_at = mapped_column(UTCDateTime, nullable=False)
    case_id = mapped_column(Text, ForeignKey("case.id"), nullable=False)
    section_id = mapped_column(Integer, nullable=False)
    parent_id = mapped_column(Text, ForeignKey("draft_version.id"), nullable=True)
    text = mapped_column(Text, nullable=False)
    claim_spans = mapped_column(JSON, nullable=False)
    computed_value_ids = mapped_column(JSON, nullable=False)
    document_ids = mapped_column(JSON, nullable=False)
    ca_input_ids = mapped_column(JSON, nullable=False)
    config_hash = mapped_column(Text, nullable=False)
    prompt_version = mapped_column(Text, nullable=False)
    model_version = mapped_column(Text, nullable=False)
    template_version_id = mapped_column(Text, ForeignKey("template_version.id"), nullable=False)
    input_fingerprint = mapped_column(Text, nullable=False)
    author = mapped_column(Text, nullable=False)
    ca_edits = mapped_column(Boolean, nullable=False)
    gaps = mapped_column(JSON, nullable=False)

class ESVersion(Base):
    __tablename__ = 'e_s_version'
    id = mapped_column(Text, primary_key=True)
    created_at = mapped_column(UTCDateTime, nullable=False)
    case_id = mapped_column(Text, ForeignKey("case.id"), nullable=False)
    parent_id = mapped_column(Text, ForeignKey("e_s_version.id"), nullable=True)
    section_versions = mapped_column(JSON, nullable=False)
    config_hash = mapped_column(Text, nullable=False)
    template_version_id = mapped_column(Text, ForeignKey("template_version.id"), nullable=False)
    author = mapped_column(Text, nullable=False)
    purpose = mapped_column(Text, nullable=False)
    gap_reasons = mapped_column(JSON, nullable=False)
    __table_args__ = (CheckConstraint("purpose IN ('working', 'export', 'submission', 'approved', 'approved with conditions', 'declined')"),)

class ChatMessage(Base):
    __tablename__ = 'chat_message'
    id = mapped_column(Text, primary_key=True)
    created_at = mapped_column(UTCDateTime, nullable=False)
    case_id = mapped_column(Text, ForeignKey("case.id"), nullable=False)
    section_id = mapped_column(Integer, nullable=False)
    base_draft_id = mapped_column(Text, ForeignKey("draft_version.id"), nullable=False)
    actor = mapped_column(Text, nullable=False)
    text = mapped_column(Text, nullable=False)

class CAInput(Base):
    __tablename__ = 'c_a_input'
    id = mapped_column(Text, primary_key=True)
    created_at = mapped_column(UTCDateTime, nullable=False)
    case_id = mapped_column(Text, ForeignKey("case.id"), nullable=False)
    message_id = mapped_column(Text, ForeignKey("chat_message.id"), nullable=False)
    supersedes_id = mapped_column(Text, ForeignKey("c_a_input.id"), nullable=True)
    revision = mapped_column(Integer, nullable=False)
    actor = mapped_column(Text, nullable=False)
    fact = mapped_column(Text, nullable=False)
    numeric_input = mapped_column(JSON, nullable=True)

class Evidence(Base):
    __tablename__ = 'evidence'
    id = mapped_column(Text, primary_key=True)
    created_at = mapped_column(UTCDateTime, nullable=False)
    case_id = mapped_column(Text, ForeignKey("case.id"), nullable=False)
    document_id = mapped_column(Text, ForeignKey("document.id"), nullable=True)
    ca_input_id = mapped_column(Text, ForeignKey("c_a_input.id"), nullable=True)
    page = mapped_column(Integer, nullable=True)
    printed_page = mapped_column(Text, nullable=True)
    region = mapped_column(Text, nullable=True)
    excerpt = mapped_column(Text, nullable=False)
    origin = mapped_column(Text, nullable=False)
    synthetic = mapped_column(Boolean, nullable=False)
    url = mapped_column(Text, nullable=True)
    retrieved_at = mapped_column(UTCDateTime, nullable=True)
    __table_args__ = (CheckConstraint("origin IN ('upload', 'folder', 'public', 'generated', 'CA input')"),)

class EvidenceIndex(Base):
    __tablename__ = 'evidence_index'
    id = mapped_column(Text, primary_key=True)
    created_at = mapped_column(UTCDateTime, nullable=False)
    case_id = mapped_column(Text, ForeignKey('case.id'), nullable=False)
    document_id = mapped_column(Text, ForeignKey('document.id'), nullable=False)
    normalizer_version = mapped_column(Text, nullable=False)
    evidence_ids = mapped_column(JSON, nullable=False)
    locators = mapped_column(JSON, nullable=False)
    gaps = mapped_column(JSON, nullable=False)
    __table_args__ = (UniqueConstraint('document_id', 'normalizer_version'),)


class Citation(Base):
    __tablename__ = 'citation'
    id = mapped_column(Text, primary_key=True)
    created_at = mapped_column(UTCDateTime, nullable=False)
    case_id = mapped_column(Text, ForeignKey("case.id"), nullable=False)
    evidence_id = mapped_column(Text, ForeignKey("evidence.id"), nullable=False)
    draft_id = mapped_column(Text, ForeignKey("draft_version.id"), nullable=True)
    computed_value_id = mapped_column(Text, ForeignKey("computed_value.id"), nullable=True)
    claim_or_cell = mapped_column(Text, nullable=False)

class Spread(Base):
    __tablename__ = 'spread'
    id = mapped_column(Text, primary_key=True)
    created_at = mapped_column(UTCDateTime, nullable=False)
    case_id = mapped_column(Text, ForeignKey("case.id"), nullable=False)
    document_ids = mapped_column(JSON, nullable=False)
    ca_input_ids = mapped_column(JSON, nullable=False)
    version = mapped_column(Text, nullable=False)
    values = mapped_column(JSON, nullable=False)
    validation_status = mapped_column(Text, nullable=False)
    issues = mapped_column(JSON, nullable=False)
    __table_args__ = (CheckConstraint("validation_status IN ('pending', 'valid', 'invalid', 'manual review')"),)

class ComputedValue(Base):
    __tablename__ = 'computed_value'
    id = mapped_column(Text, primary_key=True)
    created_at = mapped_column(UTCDateTime, nullable=False)
    case_id = mapped_column(Text, ForeignKey("case.id"), nullable=False)
    spread_id = mapped_column(Text, ForeignKey("spread.id"), nullable=True)
    metric = mapped_column(Text, nullable=False)
    formula_version = mapped_column(Text, nullable=False)
    operands = mapped_column(JSON, nullable=False)
    operand_evidence_ids = mapped_column(JSON, nullable=False)
    unit = mapped_column(Text, nullable=False)
    currency = mapped_column(Text, nullable=True)
    period = mapped_column(Text, nullable=False)
    scope = mapped_column(Text, nullable=False)
    value = mapped_column(ExactDecimal, nullable=True)
    validated = mapped_column(Boolean, nullable=False)
    proxy = mapped_column(Boolean, nullable=False)
    synthetic = mapped_column(Boolean, nullable=False)
    gaps = mapped_column(JSON, nullable=False)

class SectionProposal(Base):
    __tablename__ = 'section_proposal'
    payload = mapped_column(JSON, nullable=False)
    id = mapped_column(Text, primary_key=True)
    created_at = mapped_column(UTCDateTime, nullable=False)
    case_id = mapped_column(Text, ForeignKey("case.id"), nullable=False)
    message_id = mapped_column(Text, ForeignKey("chat_message.id"), nullable=False)
    section_id = mapped_column(Integer, nullable=False)
    base_draft_id = mapped_column(Text, ForeignKey("draft_version.id"), nullable=False)
    proposed_text = mapped_column(Text, nullable=False)
    evidence_ids = mapped_column(JSON, nullable=False)
    computed_value_ids = mapped_column(JSON, nullable=False)
    model_version = mapped_column(Text, nullable=False)
    status = mapped_column(Text, nullable=False)
    resolved_by = mapped_column(Text, nullable=True)
    resolved_at = mapped_column(UTCDateTime, nullable=True)
    accepted_draft_id = mapped_column(Text, ForeignKey("draft_version.id"), nullable=True)
    __table_args__ = (CheckConstraint("status IN ('pending', 'accepted', 'rejected', 'stale')"),)

class WorkflowEvent(Base):
    __tablename__ = 'workflow_event'
    id = mapped_column(Text, primary_key=True)
    created_at = mapped_column(UTCDateTime, nullable=False)
    case_id = mapped_column(Text, ForeignKey("case.id"), nullable=False)
    action = mapped_column(Text, nullable=False)
    actor = mapped_column(Text, nullable=False)
    role = mapped_column(Text, nullable=False)
    from_state = mapped_column(Text, nullable=False)
    to_state = mapped_column(Text, nullable=False)
    es_version_id = mapped_column(Text, ForeignKey("e_s_version.id"), nullable=False)
    returned_sections = mapped_column(JSON, nullable=False)
    override_reason = mapped_column(Text, nullable=True)
    payload = mapped_column(JSON, nullable=False)
    __table_args__ = (CheckConstraint("role IN ('CA', 'Credit Head', 'Credit Approver', 'template admin', 'credit admin support')"), CheckConstraint("from_state IN ('Draft', 'Submitted to Credit Head', 'Supported', 'With Credit Approver', 'Returned to CA', 'Question to CA', 'Approved', 'Approved with conditions', 'Declined')"), CheckConstraint("to_state IN ('Draft', 'Submitted to Credit Head', 'Supported', 'With Credit Approver', 'Returned to CA', 'Question to CA', 'Approved', 'Approved with conditions', 'Declined')"),)

class Comment(Base):
    __tablename__ = 'comment'
    id = mapped_column(Text, primary_key=True)
    created_at = mapped_column(UTCDateTime, nullable=False)
    case_id = mapped_column(Text, ForeignKey("case.id"), nullable=False)
    section_id = mapped_column(Integer, nullable=True)
    draft_id = mapped_column(Text, ForeignKey("draft_version.id"), nullable=True)
    es_version_id = mapped_column(Text, ForeignKey("e_s_version.id"), nullable=True)
    author = mapped_column(Text, nullable=False)
    role = mapped_column(Text, nullable=False)
    body = mapped_column(Text, nullable=False)
    parent_id = mapped_column(Text, ForeignKey("comment.id"), nullable=True)
    resolved_at = mapped_column(UTCDateTime, nullable=True)
    __table_args__ = (CheckConstraint("role IN ('CA', 'Credit Head', 'Credit Approver', 'template admin', 'credit admin support')"),)

class SubmissionCheck(Base):
    __tablename__ = 'submission_check'
    id = mapped_column(Text, primary_key=True)
    created_at = mapped_column(UTCDateTime, nullable=False)
    case_id = mapped_column(Text, ForeignKey("case.id"), nullable=False)
    es_version_id = mapped_column(Text, ForeignKey("e_s_version.id"), nullable=False)
    section_results = mapped_column(JSON, nullable=False)
    mandatory_gap_reasons = mapped_column(JSON, nullable=False)
    freshness_results = mapped_column(JSON, nullable=False)
    passed = mapped_column(Boolean, nullable=False)
    checked_by = mapped_column(Text, nullable=False)
    report = mapped_column(JSON, nullable=False, default=dict)

class ApproverQuestion(Base):
    __tablename__ = 'approver_question'
    id = mapped_column(Text, primary_key=True)
    created_at = mapped_column(UTCDateTime, nullable=False)
    case_id = mapped_column(Text, ForeignKey("case.id"), nullable=False)
    es_version_id = mapped_column(Text, ForeignKey("e_s_version.id"), nullable=False)
    section_ids = mapped_column(JSON, nullable=False)
    question = mapped_column(Text, nullable=False)
    asked_by = mapped_column(Text, nullable=False)
    answer = mapped_column(Text, nullable=True)
    answered_by = mapped_column(Text, nullable=True)
    answered_at = mapped_column(UTCDateTime, nullable=True)
    resubmitted_es_version_id = mapped_column(Text, ForeignKey("e_s_version.id"), nullable=True)

MODEL_BY_NAME = {model.__name__: model for model in [Case, Document, ExpectedDocument, Section, TemplateVersion, TemplateActivation, TemplateChange, DraftVersion, ESVersion, ChatMessage, CAInput, Evidence, Citation, Spread, ComputedValue, SectionProposal, WorkflowEvent, Comment, SubmissionCheck, ApproverQuestion]}
MODEL_BY_NAME['EvidenceIndex'] = EvidenceIndex

MODEL_BY_NAME['SectionConfirmation'] = SectionConfirmation


class ExportArtifact(Base):
    __tablename__ = 'export_artifact'
    id = mapped_column(Text, primary_key=True)
    created_at = mapped_column(UTCDateTime, nullable=False)
    case_id = mapped_column(Text, ForeignKey('case.id'), nullable=False)
    es_version_id = mapped_column(Text, ForeignKey('e_s_version.id'), nullable=False)
    content_hash = mapped_column(Text, nullable=False)
    manifest = mapped_column(JSON, nullable=False)


MODEL_BY_NAME['ExportArtifact'] = ExportArtifact


class TemplateComparison(Base):
    __tablename__ = 'template_comparison'
    id = mapped_column(Text, primary_key=True)
    created_at = mapped_column(UTCDateTime, nullable=False)
    team_id = mapped_column(Text, nullable=False)
    template_version_id = mapped_column(Text, ForeignKey('template_version.id'), nullable=False)
    baseline_version_id = mapped_column(Text, ForeignKey('template_version.id'), nullable=False)
    report = mapped_column(JSON, nullable=False)


MODEL_BY_NAME['TemplateComparison'] = TemplateComparison


class SenseCheck(Base):
    __tablename__ = 'sense_check'
    id = mapped_column(Text, primary_key=True)
    created_at = mapped_column(UTCDateTime, nullable=False)
    case_id = mapped_column(Text, ForeignKey('case.id'), nullable=False)
    section_id = mapped_column(Integer, nullable=False)
    draft_id = mapped_column(Text, ForeignKey('draft_version.id'), nullable=False)
    findings = mapped_column(JSON, nullable=False)
    tables_checked = mapped_column(Integer, nullable=False)
    model = mapped_column(Text, nullable=False)
    cost_usd = mapped_column(Text, nullable=True)
    checked_by = mapped_column(Text, nullable=False)
    resolutions = mapped_column(JSON, nullable=False, default=dict)


MODEL_BY_NAME['SenseCheck'] = SenseCheck


class ReviewMark(Base):
    __tablename__ = 'review_mark'
    id = mapped_column(Text, primary_key=True)
    created_at = mapped_column(UTCDateTime, nullable=False)
    case_id = mapped_column(Text, ForeignKey('case.id'), nullable=False)
    section_id = mapped_column(Integer, nullable=False)
    draft_id = mapped_column(Text, ForeignKey('draft_version.id'), nullable=False)
    es_version_id = mapped_column(Text, ForeignKey('e_s_version.id'), nullable=False)
    reviewer = mapped_column(Text, nullable=False)
    role = mapped_column(Text, nullable=False)
    status = mapped_column(Text, nullable=False)
    note = mapped_column(Text, nullable=False, default='')


MODEL_BY_NAME['ReviewMark'] = ReviewMark


class UpdateProposal(Base):
    __tablename__ = 'update_proposal'
    id = mapped_column(Text, primary_key=True)
    created_at = mapped_column(UTCDateTime, nullable=False)
    case_id = mapped_column(Text, ForeignKey('case.id'), nullable=False)
    section_id = mapped_column(Integer, nullable=False)
    base_draft_id = mapped_column(Text, ForeignKey('draft_version.id'), nullable=False)
    input_fingerprint = mapped_column(Text, nullable=False)
    documents_key = mapped_column(Text, nullable=False)
    candidate = mapped_column(JSON, nullable=False)
    changes = mapped_column(JSON, nullable=False)
    kept = mapped_column(JSON, nullable=False)
    proposed_by = mapped_column(Text, nullable=False)
    cost_usd = mapped_column(Text, nullable=True)
    status = mapped_column(Text, nullable=False)
    decisions = mapped_column(JSON, nullable=False, default=dict)
    resolved_by = mapped_column(Text, nullable=True)
    resolved_at = mapped_column(UTCDateTime, nullable=True)
    applied_draft_id = mapped_column(Text, ForeignKey('draft_version.id'), nullable=True)


MODEL_BY_NAME['UpdateProposal'] = UpdateProposal
