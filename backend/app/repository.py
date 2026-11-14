"""Validated CRUD seam. Later services own transitions and readiness decisions."""
from sqlalchemy import JSON, select

from . import models, schemas
from .team_config import TeamConfig, load_team

IMMUTABLE = {'DraftVersion', 'ESVersion', 'Evidence', 'Citation', 'CAInput', 'Spread', 'ComputedValue', 'WorkflowEvent', 'TemplateVersion', 'TemplateActivation', 'ChatMessage', 'SubmissionCheck'}
COLLECTION_REFS = {
    'document_ids': 'Document', 'ca_input_ids': 'CAInput',
    'computed_value_ids': 'ComputedValue', 'evidence_ids': 'Evidence',
    'section_versions': 'DraftVersion', 'operand_evidence_ids': 'Evidence',
}
IMMUTABLE.update({'EvidenceIndex', 'SectionConfirmation', 'ExportArtifact'})
IMMUTABLE.add('TemplateComparison')
IMMUTABLE.add('ReviewMark')


class Repository:
    def __init__(self, session, config_loader=load_team):
        self.session = session
        self.config_loader = config_loader

    def get(self, schema, record_id):
        model = models.MODEL_BY_NAME[schema.__name__]
        row = self.session.get(model, record_id)
        if row is None:
            raise ValueError(f'{schema.__name__} not found: {record_id}')
        return schema.model_validate({name: getattr(row, name) for name in schema.model_fields})

    def save(self, record):
        schema = getattr(schemas, type(record).__name__)
        record = schema.model_validate(record.model_dump())
        model = models.MODEL_BY_NAME[schema.__name__]
        existing = self.session.get(model, record.id)
        if existing and schema.__name__ in IMMUTABLE:
            raise ValueError(f'{schema.__name__} is append-only')
        if existing and hasattr(record, 'case_id') and record.case_id != existing.case_id:
            raise ValueError('Cannot move a record to another case')
        case = record if isinstance(record, schemas.Case) else self.get(schemas.Case, record.case_id) if hasattr(record, 'case_id') else None
        if case and case.config_snapshot:
            config = TeamConfig.model_validate(case.config_snapshot)
        else:
            config = self.config_loader(case.team_id if case else record.team_id) if case or hasattr(record, 'team_id') else None
        # Defense in depth for callers that bypass the public mutation services.
        from .services.locks import require_working
        derived_stale = (isinstance(record, schemas.SectionProposal) and existing
                         and record.status == 'stale' and existing.status == 'pending'
                         and all(getattr(record, f) == getattr(existing, f)
                                 for f in schema.model_fields if f != 'status'))
        if isinstance(record, (schemas.DraftVersion, schemas.ChatMessage, schemas.CAInput,
                               schemas.SectionProposal, schemas.SectionConfirmation,
                               schemas.Spread, schemas.ComputedValue)) and not derived_stale:
            require_working(self, record.case_id, getattr(record, 'section_id', None))
        if isinstance(record, schemas.Document):
            require_working(self, record.case_id, intake=not existing)
        if isinstance(record, schemas.Section) and existing:
            if any(getattr(record, f) != getattr(existing, f) for f in ('current_draft_id', 'confirmed_draft_id')):
                require_working(self, record.case_id, record.section_id)
        if isinstance(record, schemas.Case) and existing:
            if any(getattr(record, f) != getattr(existing, f) for f in ('ca_position', 'default_model_id')):
                require_working(self, record.id)
        if isinstance(record, schemas.TemplateChange):
            config = self.config_loader(self.get(schemas.TemplateVersion, record.template_version_id).team_id)
        if isinstance(record, schemas.Case):
            if record.team_id != config.template.team_id or record.config_hash != config.content_hash or record.config_version != config.template.version:
                raise ValueError('Case must pin the loaded configuration version/hash')
            if existing and any(getattr(record, f) != getattr(existing, f) for f in ('team_id', 'config_version', 'config_hash')):
                raise ValueError('Case configuration pin is immutable')
            record.config_snapshot = config.model_dump(mode='json', exclude_unset=True)
        if isinstance(record, (schemas.DraftVersion, schemas.ESVersion)) and record.config_hash != case.config_hash:
            raise ValueError('Version must pin the case configuration')
        if config:
            section_ids = {s.id for s in config.template.sections}
            for field in ('section_id', 'section_ids', 'returned_sections', 'section_versions', 'section_results', 'freshness_results'):
                value = getattr(record, field, None)
                values = value if isinstance(value, (dict,list)) else [] if value is None else [value]
                if not set(values) <= section_ids:
                    raise ValueError('Unknown configured section')
            catalogue_id = getattr(record, 'catalogue_id', None)
            if catalogue_id is not None and catalogue_id not in {i.id for i in config.catalogue.items}:
                raise ValueError('Unknown catalogue type')
        # All scalar foreign keys must exist and belong to the same case/team.
        refs = []
        for column in model.__table__.columns:
            value = getattr(record, column.name)
            if value is not None:
                for fk in column.foreign_keys:
                    target = next(m for m in models.MODEL_BY_NAME.values() if m.__tablename__ == fk.column.table.name)
                    refs.append((column.name, target, value))
        for field, target_name in COLLECTION_REFS.items():
            values = getattr(record, field, [])
            if isinstance(values, dict):
                values = list(values.values())
                if field == 'operand_evidence_ids':
                    values = [ref for group in values for ref in group]
            refs.extend((field, models.MODEL_BY_NAME[target_name], value) for value in values)
        for field, target, value in refs:
            linked = self.session.get(target, value)
            if linked is None:
                raise ValueError(f'Missing {field} reference: {value}')
            if case and hasattr(linked, 'case_id') and linked.case_id != case.id:
                raise ValueError('Cross-case reference rejected')
            if case and hasattr(linked, 'team_id') and linked.team_id != case.team_id:
                raise ValueError('Cross-team reference rejected')
            if hasattr(record, 'team_id') and hasattr(linked, 'team_id') and record.team_id != linked.team_id:
                raise ValueError('Cross-team template reference rejected')
            if hasattr(record, 'section_id') and hasattr(linked, 'section_id') and linked.section_id is not None and record.section_id != linked.section_id:
                raise ValueError('Cross-section reference rejected')
        if isinstance(record, schemas.WorkflowEvent):
            if not any(t.enabled and t.action == record.action and t.role == record.role and record.from_state in t.from_states and t.to_state == record.to_state for t in config.workflow.transitions):
                raise ValueError('Invalid configured workflow event')
        if isinstance(record, schemas.ESVersion):
            for section, draft_id in record.section_versions.items():
                if self.get(schemas.DraftVersion, draft_id).section_id != section:
                    raise ValueError('Snapshot section does not match draft')
        if isinstance(record, schemas.ApproverQuestion) and existing:
            mutable = {'answer', 'answered_by', 'answered_at', 'resubmitted_es_version_id'}
            if (existing.answer is not None or not record.answer or not record.resubmitted_es_version_id
                    or any(getattr(record, f) != getattr(existing, f) for f in schema.model_fields if f not in mutable)):
                raise ValueError('Question content and completed answers are immutable')
        if isinstance(record, schemas.SectionProposal) and existing:
            mutable = {'status', 'resolved_by', 'resolved_at', 'accepted_draft_id'}
            if existing.status != 'pending' or any(getattr(record, f) != getattr(existing, f)
                    for f in schema.model_fields if f not in mutable):
                raise ValueError('Proposal content/resolution is immutable')
        if isinstance(record, schemas.Document) and existing:
            old = self.get(schemas.Document, record.id)
            mutable = {'confirmed_by', 'confirmed_at', 'conflict_status'}
            if any(getattr(old, field) != getattr(record, field) for field in schema.model_fields if field not in mutable):
                raise ValueError('Document content/version metadata is immutable')
        if isinstance(record, schemas.Evidence) and record.document_id:
            document = self.get(schemas.Document, record.document_id)
            if any(getattr(record, f) != getattr(document, f) for f in ('origin','synthetic','url','retrieved_at')):
                raise ValueError('Evidence provenance must match document version')
        if isinstance(record, schemas.EvidenceIndex):
            if set(record.evidence_ids) != set(record.locators):
                raise ValueError('Index locators must match evidence IDs')
            if any(self.get(schemas.Evidence, ref).document_id != record.document_id for ref in record.evidence_ids):
                raise ValueError('Index evidence must belong to its document version')
        if isinstance(record, schemas.ComputedValue):
            evidence = [self.get(schemas.Evidence, ref) for refs in record.operand_evidence_ids.values() for ref in refs]
            if any(e.synthetic for e in evidence) and not record.synthetic:
                raise ValueError('Derived values must retain synthetic label')
        plain = record.model_dump()
        json_values = record.model_dump(mode='json')
        data = {c.name: json_values[c.name] if isinstance(c.type, JSON) else plain[c.name] for c in model.__table__.columns}
        if existing:
            for key, value in data.items():
                setattr(existing, key, value)
        else:
            self.session.add(model(**data))
        self.session.flush()
        return record

    def list_for_case(self, schema, case_id):
        model = models.MODEL_BY_NAME[schema.__name__]
        return [self.get(schema, row.id) for row in self.session.scalars(select(model).where(model.case_id == case_id))]
