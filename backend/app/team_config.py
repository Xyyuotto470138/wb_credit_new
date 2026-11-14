"""Safe, versioned team configuration; shared vocabulary, no team-specific branches."""
import hashlib
import json
import re
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from .schemas import Case, Role, WorkflowState
from .extraction_agent.contracts import SpreadProfile

CONFIG_ROOT = Path(__file__).resolve().parents[2] / 'config' / 'teams'


class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid')


class Predicate(Strict):
    op: Literal['always', 'eq', 'in', 'contains', 'all', 'any', 'not']
    field: str | None = None
    value: str | bool | list[str] | None = None
    args: list['Predicate'] = Field(default_factory=list)

    @model_validator(mode='after')
    def shape(self):
        if self.op in ('all', 'any', 'not'):
            if self.field is not None or self.value is not None or not self.args or (self.op == 'not' and len(self.args) != 1):
                raise ValueError('Invalid logical predicate')
        elif self.op == 'always':
            if self.field is not None or self.value is not None or self.args:
                raise ValueError('always takes no arguments')
        else:
            allowed = {'case_type', 'borrower_type', 'facility_types', 'existing_client', 'new_to_bank', 'property_or_asset_security', 'insured_security_or_assets', 'financial_covenants', 'covenants', 'new_money', 'property_income_repayment', 'bureau_covered', 'has_information_memorandum', 'public_entity'}
            if self.field not in allowed or self.value is None or self.args:
                raise ValueError('Invalid case predicate field/value')
            if self.op == 'in' and not isinstance(self.value, list):
                raise ValueError('in requires a list')
            if self.op == 'contains' and (self.field != 'facility_types' or not isinstance(self.value, str)):
                raise ValueError('contains requires a facility type')
            if self.field not in {'case_type', 'borrower_type', 'facility_types'} and (self.op != 'eq' or not isinstance(self.value, bool)):
                raise ValueError('Boolean case attributes require boolean equality')
            if self.field == 'case_type' and any(v not in ('new', 'renewal') for v in (self.value if isinstance(self.value, list) else [self.value])):
                raise ValueError('Unknown case type')
        return self

    def matches(self, case: Case) -> bool:
        if self.op == 'always':
            return True
        if self.op == 'all':
            return all(arg.matches(case) for arg in self.args)
        if self.op == 'any':
            return any(arg.matches(case) for arg in self.args)
        if self.op == 'not':
            return not self.args[0].matches(case)
        actual = getattr(case, self.field)
        if self.op == 'eq':
            return actual == self.value
        if self.op == 'in':
            return actual in self.value
        return self.value in actual


class SectionDefinition(Strict):
    id: int = Field(ge=1)
    name: str
    description: str
    main_inputs: str
    case_rule: str
    draft_mode: str
    mandatory_when: Predicate
    applicable_when: Predicate
    requires_ca_position: bool = False
    requires_supplied_internal_rating: bool = False
    unsecured_requires_ca_confirmation: bool = False


class MappingRules(Strict):
    heading_style: str
    numbered_headings: bool
    recursive_tables: bool
    table_match: str
    placeholders: str
    missing_anchor: str
    layout_source: str


class TemplateTableAnchor(Strict):
    id: str = Field(pattern=r'^[a-z][a-z0-9_]*$')
    section_id: int = Field(ge=0)
    headers: list[str] = Field(min_length=1)
    row_labels: list[str] = Field(default_factory=list)
    cell_spans: list[list[int]] = Field(default_factory=list)
    kind: Literal['records', 'key_value', 'matrix', 'checkboxes', 'chart'] = 'records'
    repeat: Literal['none', 'rows', 'facility_columns', 'covenant_rows'] = 'none'
    source_policy: str = Field(min_length=1)


class TemplateNarrativeAnchor(Strict):
    section_id: int = Field(ge=1)
    text: str = Field(min_length=1)


class TemplateConfig(Strict):
    team_id: str
    version: str
    default_template: str
    mapping: MappingRules
    sections: list[SectionDefinition]
    table_anchors: list[TemplateTableAnchor] = Field(default_factory=list)
    narrative_anchors: list[TemplateNarrativeAnchor] = Field(default_factory=list)

    @model_validator(mode='after')
    def anchors(self):
        ids = {s.id for s in self.sections}
        if len({a.id for a in self.table_anchors}) != len(self.table_anchors):
            raise ValueError('Duplicate template anchor ID')
        if any(a.section_id not in ids | {0} for a in self.table_anchors):
            raise ValueError('Unknown template anchor section')
        if any(a.section_id not in ids for a in self.narrative_anchors):
            raise ValueError('Unknown template narrative section')
        return self


class CatalogueItem(Strict):
    id: int = Field(ge=1)
    name: str
    usual_source: str
    owner_group: Literal['RM', 'client', 'internal team']
    public_availability: str
    applies_when: str
    sections: list[int]
    mandatory_label: str
    applicable_when: Predicate
    mandatory_when: Predicate
    alternative_group: str | None = None
    public_search: bool
    public_support: Literal['full after confirmation', 'partial only', 'external only', 'none']
    generated: bool = False
    confirmation_required: bool = False
    generation: Literal['spread', 'industry code'] | None = None
    generation_inputs: list[int] = Field(default_factory=list)


class CatalogueConfig(Strict):
    items: list[CatalogueItem]


class AlternativeGroup(Strict):
    id: str
    members: list[int]
    minimum: int = Field(ge=1)


class Suggestion(Strict):
    public_search: bool = False
    id: str
    name: str
    sections: list[int]
    status: Literal['Suggested'] = 'Suggested'
    owner_group: Literal['RM', 'client', 'internal team'] = 'internal team'
    when: Predicate | None = None
    trigger_catalogue_ids: list[int] = Field(default_factory=list)
    reason: str = 'Supporting evidence suggested for review.'


class DraftGate(Strict):
    section_id: int
    when: Predicate
    any_inputs: list[int]
    reason: str


class RulesConfig(Strict):
    version: str
    alternatives: list[AlternativeGroup]
    suggestions: list[Suggestion]
    public_confirmation_required: bool
    generated_spread_requires_validation: bool
    industry_code_requires_confirmation: bool
    external_rating_satisfies_internal: Literal[False]
    partial_disclosure_satisfies_full_report: Literal[False]
    missing_document_is_fact: Literal[False]
    draft_gates: list[DraftGate] = Field(default_factory=list)


class Dependency(Strict):
    section_id: int
    requires: list[int]
    freshness_requires: list[int] = Field(default_factory=list)
    applicable_only: bool = True
    mandatory_only: bool = False
    ca_position: bool = False


class DependenciesConfig(Strict):
    items: list[Dependency]


class Formula(Strict):
    op: Literal['reported', 'ratio', 'subtract', 'sum', 'weighted_average', 'bucket_sum', 'ebitda_stress', 'interest_stress']
    operands: list[str]

    @model_validator(mode='after')
    def arity(self):
        sizes = {'reported': 1, 'ratio': 2, 'subtract': 2, 'weighted_average': 2, 'bucket_sum': 2, 'ebitda_stress': 2, 'interest_stress': 3}
        if not self.operands or (self.op in sizes and len(self.operands) != sizes[self.op]):
            raise ValueError('Invalid formula operands')
        return self


class Threshold(Strict):
    value: str
    comparison: Literal['maximum', 'minimum', 'flag_below']
    headroom: Formula | None = None
    source: str
    effective_date: str
    verification: Literal['pending B10', 'MAS source checked 2026-11-10']


class Metric(Strict):
    id: str
    name: str
    unit: str
    formula: Formula
    reported_fallback: bool
    definition: str
    thresholds: list[Threshold] = Field(default_factory=list)
    input_units: dict[str, str] = Field(default_factory=dict)
    required_basis: str | None = None
    multiplier: str = '1'
    minimum: str | None = None
    maximum: str | None = None
    nonnegative: bool = False
    forbid_proxy: bool = False
    reconcile_to: str | None = None
    tolerance: str = '0'
    template_rows: list[str] = Field(default_factory=list)
    source_labels: list[str] = Field(default_factory=list)
    allowed_bases: list[str] = Field(default_factory=list)

    @model_validator(mode='after')
    def numeric_rules(self):
        from decimal import Decimal, InvalidOperation
        try:
            for value in [self.multiplier, self.minimum, self.maximum, self.tolerance]:
                if value is not None and not Decimal(value).is_finite():
                    raise ValueError('Nonfinite analytics parameter')
            if Decimal(self.tolerance) < 0:
                raise ValueError('Negative reconciliation tolerance')
        except InvalidOperation as error:
            raise ValueError('Invalid analytics parameter') from error
        if self.input_units and set(self.input_units) != set(self.formula.operands) | ({self.reconcile_to} if self.reconcile_to else set()):
            raise ValueError('Input units must cover formula and reconciliation operands')
        return self


class AnalyticsSet(Strict):
    borrower_types: list[str]
    metrics: list[Metric]


class AnalyticsConfig(Strict):
    version: str
    sets: dict[str, AnalyticsSet]
    missing_operand_policy: Literal['N/A with named gap']
    arithmetic: Literal['Python Decimal']
    spreading: dict[str, SpreadProfile] = Field(default_factory=dict)

    @model_validator(mode='after')
    def spread_profiles(self):
        for profile in self.spreading.values():
            SpreadProfile.validate_profile(profile)
        return self


class Prompt(Strict):
    section_id: int
    instruction: str


class PromptsConfig(Strict):
    version: str
    common: list[str]
    items: list[Prompt]


class Transition(Strict):
    action: Literal['submit', 'support', 'handoff', 'return', 'approve', 'approve_with_conditions', 'question', 'decline', 'answer_resubmit']
    role: Role
    from_states: list[WorkflowState]
    to_state: WorkflowState
    requirements: list[Literal['submission_checks', 'named_sections', 'comment', 'conditions', 'question', 'answer']]
    enabled: bool = True


class WorkflowConfig(Strict):
    roles: list[Role]
    initial_state: WorkflowState
    states: list[WorkflowState]
    final_states: list[WorkflowState]
    locked_states: list[WorkflowState]
    transitions: list[Transition]
    credit_admin_support_enabled: bool
    question_edit_scope: Literal['answer only']

    @model_validator(mode='after')
    def valid_workflow(self):
        states, roles = set(self.states), set(self.roles)
        if len(states) != len(self.states) or len(roles) != len(self.roles):
            raise ValueError('Duplicate states or roles')
        if self.initial_state not in states or not set(self.final_states + self.locked_states) <= states:
            raise ValueError('Unknown workflow state')
        finals = {'Approved', 'Approved with conditions', 'Declined'}
        if not finals <= set(self.final_states):
            raise ValueError('Final outcomes must remain final')
        if not (finals | {'Submitted to Credit Head', 'Supported', 'With Credit Approver', 'Question to CA'}) <= set(self.locked_states):
            raise ValueError('Reviewer and final states must remain locked')
        if self.initial_state != 'Draft' or {'Draft', 'Returned to CA'} & set(self.locked_states):
            raise ValueError('Working states must remain editable')
        seen = set()
        permission = {'submit': 'CA', 'support': 'Credit Head', 'handoff': 'Credit Head', 'approve': 'Credit Approver', 'approve_with_conditions': 'Credit Approver', 'question': 'Credit Approver', 'decline': 'Credit Approver', 'answer_resubmit': 'CA'}
        if self.credit_admin_support_enabled:
            # Reserved S06 insertion seam: Supported is held by the admin role
            # before its configured handoff. No admin UI/checks are implemented.
            permission['handoff'] = 'credit admin support'
        destinations = {'submit': 'Submitted to Credit Head', 'support': 'Supported', 'handoff': 'With Credit Approver', 'return': 'Returned to CA', 'approve': 'Approved', 'approve_with_conditions': 'Approved with conditions', 'question': 'Question to CA', 'decline': 'Declined', 'answer_resubmit': 'With Credit Approver'}
        for t in self.transitions:
            if t.role not in roles or t.to_state not in states or not set(t.from_states) <= states or not t.from_states:
                raise ValueError('Unknown workflow reference')
            if set(t.from_states) & set(self.final_states):
                raise ValueError('Final outcomes cannot transition')
            if (t.action in permission and t.role != permission[t.action]) or (t.action == 'return' and t.role not in ('Credit Head', 'Credit Approver')):
                raise ValueError('Role cannot perform this outcome')
            source_states = {
                'submit': {'Draft', 'Returned to CA'}, 'support': {'Submitted to Credit Head'},
                'handoff': {'Supported'}, 'approve': {'With Credit Approver'},
                'approve_with_conditions': {'With Credit Approver'}, 'question': {'With Credit Approver'},
                'decline': {'With Credit Approver'}, 'answer_resubmit': {'Question to CA'},
                'return': {'Submitted to Credit Head'} if t.role == 'Credit Head' else {'With Credit Approver'},
            }
            if not set(t.from_states) <= source_states[t.action]:
                raise ValueError('Invalid outcome source state')
            if t.to_state != destinations[t.action]:
                raise ValueError('Invalid outcome destination')
            required = {'return': {'named_sections', 'comment'}, 'approve_with_conditions': {'conditions'}, 'question': {'question'}, 'answer_resubmit': {'answer', 'submission_checks'}, 'submit': {'submission_checks'}}.get(t.action, set())
            if not required <= set(t.requirements):
                raise ValueError('Outcome missing required evidence')
            for state in t.from_states:
                key = (state, t.role, t.action)
                if key in seen:
                    raise ValueError('Duplicate transition')
                seen.add(key)
        return self


class TeamConfig(Strict):
    template: TemplateConfig
    catalogue: CatalogueConfig
    rules: RulesConfig
    dependencies: DependenciesConfig
    analytics: AnalyticsConfig
    prompts: PromptsConfig
    workflow: WorkflowConfig

    @model_validator(mode='after')
    def references(self):
        sections = {s.id for s in self.template.sections}
        catalogue = {i.id for i in self.catalogue.items}
        if not sections or len(sections) != len(self.template.sections) or len(catalogue) != len(self.catalogue.items):
            raise ValueError('Empty or duplicate configuration IDs')
        for item in [*self.catalogue.items, *self.rules.suggestions]:
            if not set(item.sections) <= sections:
                raise ValueError('Unknown section reference')
        for item in self.catalogue.items:
            if not set(item.generation_inputs) <= catalogue:
                raise ValueError('Unknown generation input')
        if len({s.id for s in self.rules.suggestions}) != len(self.rules.suggestions):
            raise ValueError('Duplicate suggestion ID')
        for suggestion in self.rules.suggestions:
            if not set(suggestion.trigger_catalogue_ids) <= catalogue:
                raise ValueError('Unknown suggestion trigger')
        for gate in self.rules.draft_gates:
            if gate.section_id not in sections or not gate.any_inputs or not set(gate.any_inputs) <= catalogue:
                raise ValueError('Invalid draft gate')
        groups = {g.id: g for g in self.rules.alternatives}
        if len(groups) != len(self.rules.alternatives):
            raise ValueError('Duplicate alternative group')
        for group in groups.values():
            if not set(group.members) <= catalogue or len(set(group.members)) != len(group.members) or group.minimum > len(group.members):
                raise ValueError('Invalid alternative group')
            if {i.id for i in self.catalogue.items if i.alternative_group == group.id} != set(group.members):
                raise ValueError('Alternative membership must agree')
        for item in self.catalogue.items:
            if item.alternative_group and item.alternative_group not in groups:
                raise ValueError('Unknown alternative group')
            if item.public_search and item.public_support == 'none':
                raise ValueError('Private types cannot be searched')
        graph = {d.section_id: d.requires + d.freshness_requires for d in self.dependencies.items}
        if len(graph) != len(self.dependencies.items) or set(graph) != sections:
            raise ValueError('Dependencies must cover every section exactly once')
        visiting, visited = set(), set()

        def visit(node):
            if node not in sections:
                raise ValueError('Unknown dependency section')
            if node in visiting:
                raise ValueError('Dependency cycle')
            if node in visited:
                return
            visiting.add(node)
            for child in graph[node]:
                visit(child)
            visiting.remove(node)
            visited.add(node)
        for node in graph:
            visit(node)
        if len(self.prompts.items) != len(sections) or {p.section_id for p in self.prompts.items} != sections:
            raise ValueError('Prompts must cover every section exactly once')
        for group in self.analytics.sets.values():
            if len({m.id for m in group.metrics}) != len(group.metrics):
                raise ValueError('Duplicate metric ID')
        return self

    @property
    def content_hash(self):
        canonical = json.dumps(self.model_dump(mode='json', exclude_unset=True), sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(canonical.encode()).hexdigest()


def load_team(team_id: str, root: Path = CONFIG_ROOT) -> TeamConfig:
    if not re.fullmatch(r'[a-z0-9][a-z0-9_-]*', team_id):
        raise ValueError('Invalid team ID')
    folder = root / team_id
    # A team may reuse another team's files: `extends.txt` names the parent, used for any file this folder lacks.
    parent = root / (folder / 'extends.txt').read_text().strip() if (folder / 'extends.txt').exists() else None
    source = lambda name: folder / f'{name}.yaml' if (folder / f'{name}.yaml').exists() or parent is None else parent / f'{name}.yaml'
    data = {name: yaml.safe_load(source(name).read_text()) for name in TeamConfig.model_fields}
    config = TeamConfig.model_validate(data)
    if config.template.team_id != team_id:
        raise ValueError('Team ID does not match directory')
    return config
