"""Configured human workflow. Callers serialize and commit the entire transaction."""
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from .. import schemas as s
from .locks import WorkflowConflict, workflow_config, returned_scope
from .submission_checks import CheckRequest, Nonblank, SubmissionChecksService
from .readiness import ReadinessService

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=10000)]


class TransitionRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    actor: str = Field(min_length=1, max_length=200, pattern=r'.*\S.*')
    role: s.Role
    action: str
    expected_state: s.WorkflowState
    expected_event_id: str | None
    expected_es_version_id: str | None
    section_ids: list[int] = Field(default_factory=list, max_length=14)
    comment: Text | None = None
    conditions: list[Text] = Field(default_factory=list, max_length=100)
    question: Text | None = None
    question_id: str | None = None
    answer: Text | None = None
    expected_preview_token: str | None = None
    mandatory_gap_reasons: dict[str, Nonblank] = Field(default_factory=dict)


class WorkflowPermission(ValueError):
    pass


class WorkflowService:
    def __init__(self, repo, storage_root, template_storage_root):
        self.repo = repo
        self.checks = SubmissionChecksService(repo, storage_root, template_storage_root)

    def view(self, case_id):
        case, config = workflow_config(self.repo, case_id)
        events = sorted(self.repo.list_for_case(s.WorkflowEvent, case_id), key=lambda e: (e.created_at, e.id))
        return dict(case_id=case_id, state=case.workflow_state, active_es_version_id=case.active_es_version_id,
            latest_event_id=events[-1].id if events else None, config_hash=case.config_hash,
            roles=config.workflow.roles, locked=case.workflow_state in config.workflow.locked_states,
            final=case.workflow_state in config.workflow.final_states,
            editable_sections=returned_scope(self.repo, case_id) if case.workflow_state == 'Returned to CA'
                else [v.id for v in config.template.sections] if case.workflow_state == config.workflow.initial_state else [],
            available_actions=[t.model_dump() for t in config.workflow.transitions
                               if t.enabled and case.workflow_state in t.from_states],
            events=events, questions=sorted(self.repo.list_for_case(s.ApproverQuestion, case_id),
                                           key=lambda q: (q.created_at, q.id)))

    def snapshot(self, case_id, es_id):
        es = self.repo.get(s.ESVersion, es_id)
        if es.case_id != case_id:
            raise ValueError('ES snapshot not found in this case')
        checks = self.repo.list_for_case(s.SubmissionCheck, case_id)
        ancestor, check = es, None
        while ancestor:
            check = next((c for c in checks if c.es_version_id == ancestor.id), None)
            if check or not ancestor.parent_id:
                break
            ancestor = self.repo.get(s.ESVersion, ancestor.parent_id)
        return dict(es=es, sections={sid: self.repo.get(s.DraftVersion, did) for sid, did in es.section_versions.items()},
            submission_check=check, events=[e for e in self.view(case_id)['events'] if e.es_version_id == es_id])

    def transition(self, case_id, request):
        case, config = workflow_config(self.repo, case_id)
        view = self.view(case_id)
        if (request.expected_state != case.workflow_state or request.expected_event_id != view['latest_event_id']
                or request.expected_es_version_id != case.active_es_version_id):
            raise WorkflowConflict('Workflow changed; reload before taking this action')
        if case.workflow_state in config.workflow.final_states:
            raise WorkflowConflict('Final outcomes cannot transition or reopen')
        candidates = [t for t in config.workflow.transitions if t.enabled and t.action == request.action
                      and case.workflow_state in t.from_states]
        transition = next((t for t in candidates if t.role == request.role), None)
        if not transition:
            if candidates:
                raise WorkflowPermission('This role cannot perform the configured action')
            raise WorkflowConflict('Action is unavailable in the current configured state')
        section_ids = set(request.section_ids)
        if len(section_ids) != len(request.section_ids) or not section_ids <= {d.id for d in config.template.sections}:
            raise ValueError('Sections must be unique configured section IDs')
        for requirement in transition.requirements:
            if requirement == 'named_sections' and not section_ids:
                raise ValueError('Return requires named sections')
            if requirement in {'comment', 'conditions', 'question', 'answer'} and not getattr(request, requirement):
                raise ValueError(f'{requirement} is required for this action')
        allowed = {'return': {'section_ids', 'comment'}, 'question': {'section_ids', 'question'},
                   'approve_with_conditions': {'conditions'}, 'answer_resubmit': {'answer', 'question_id'},
                   'submit': set()}.get(request.action, set()) | {'comment'}
        for name in ('section_ids', 'question', 'conditions', 'answer', 'question_id'):
            if getattr(request, name) and name not in allowed:
                raise ValueError(f'{name} does not apply to this action')
        gate = 'submission_checks' in transition.requirements
        if not gate and (request.expected_preview_token or request.mandatory_gap_reasons):
            raise ValueError('Submission fields do not apply to this action')
        previous = self.repo.get(s.ESVersion, case.active_es_version_id) if case.active_es_version_id else None
        if request.action != 'submit' and previous is None:
            raise WorkflowConflict('An active submitted ES snapshot is required')
        question = None
        if request.action == 'answer_resubmit':
            open_questions = [q for q in view['questions'] if q.answer is None]
            if len(open_questions) != 1 or request.question_id != open_questions[0].id:
                raise WorkflowConflict('Answer must name the current unanswered question')
            question = open_questions[0]
            if question.es_version_id != previous.id:
                raise WorkflowConflict('Question belongs to a different ES snapshot')
        check, es = None, previous
        if gate:
            if not request.expected_preview_token:
                raise ValueError('A current B25 preview token is required')
            command = CheckRequest(actor=request.actor, expected_preview_token=request.expected_preview_token,
                                   mandatory_gap_reasons=request.mandatory_gap_reasons)
            report = self.checks.require_passed(case_id, command, allowed_states={case.workflow_state})
            pins = {v['section_id']: v['draft_id'] for v in report['sections'] if v['applicable'] and v['draft_id']}
            if question and (pins != previous.section_versions or report['template_version_id'] != previous.template_version_id
                             or request.mandatory_gap_reasons != previous.gap_reasons):
                raise WorkflowConflict('Question cycle permits only an answer; return for substantive ES changes')
            check = self.checks.record_report(case_id, command, report, purpose='submission',
                                            parent_id=previous.id if previous else None)
            es = self.repo.get(s.ESVersion, check.es_version_id)
        if transition.to_state in config.workflow.final_states:
            es = self.repo.save(s.ESVersion(case_id=case_id, parent_id=previous.id,
                section_versions=previous.section_versions, config_hash=previous.config_hash,
                template_version_id=previous.template_version_id, author=request.actor,
                purpose=transition.to_state.lower(), gap_reasons=previous.gap_reasons))
        payload = dict(comment=request.comment, conditions=request.conditions,
                       submission_check_id=check.id if check else None)
        if request.action == 'question':
            question = self.repo.save(s.ApproverQuestion(case_id=case_id, es_version_id=es.id,
                section_ids=request.section_ids, question=request.question, asked_by=request.actor))
        elif question:
            question = self.repo.save(question.model_copy(update=dict(answer=request.answer,
                answered_by=request.actor, answered_at=s.utcnow(), resubmitted_es_version_id=es.id)))
        if question:
            payload['question'] = question.model_dump(mode='json')
        self.repo.save(s.WorkflowEvent(case_id=case_id, action=request.action, actor=request.actor,
            role=request.role, from_state=case.workflow_state, to_state=transition.to_state,
            es_version_id=es.id, returned_sections=request.section_ids if request.action == 'return' else [], payload=payload))
        self.repo.save(case.model_copy(update=dict(workflow_state=transition.to_state, active_es_version_id=es.id)))
        if request.action == 'return':
            scope = returned_scope(self.repo, case_id)
            for state in ReadinessService(self.repo).refresh(case_id)[1]:
                if state.section_id in scope and state.applicable:
                    self.repo.save(state.model_copy(update=dict(confirmed_draft_id=None,
                        readiness='Stale' if state.readiness == 'Stale' else 'Drafted' if state.current_draft_id else state.readiness,
                        editor_revision=state.editor_revision + 1)))
        if request.comment:
            for sid in request.section_ids or [None]:
                self.repo.save(s.Comment(case_id=case_id, section_id=sid, es_version_id=es.id,
                    author=request.actor, role=request.role, body=request.comment))
        return self.view(case_id)
