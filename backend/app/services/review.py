"""Maker and checker: what the reviewer sees and records on a submitted ES.

The workflow service owns the moves (submit, return, support). This adds the checker's working record: a mark on
each section of the submitted ES, reviewed or a query for the maker, and the read model both roles share.
A mark belongs to the exact version of the section it was made on, so a section that is unchanged on
resubmission keeps its mark and a changed section needs a fresh look. Marks record a review; they are not a
credit decision.
"""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .. import schemas as s
from .locks import WorkflowConflict, returned_scope, workflow_config

REVIEWING = {'Credit Head': 'Submitted to Credit Head', 'Credit Approver': 'With Credit Approver'}


class MarkRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    actor: str = Field(min_length=1, max_length=200, pattern=r'.*\S.*')
    role: Literal['Credit Head', 'Credit Approver']
    section_id: int
    status: Literal['reviewed', 'query', 'cleared']
    note: str = Field(default='', max_length=4000)
    expected_es_version_id: str


def latest_marks(repo, case_id):
    marks = {}
    for mark in sorted(repo.list_for_case(s.ReviewMark, case_id), key=lambda m: (m.created_at, m.id)):
        marks[mark.section_id] = mark
    return marks


def view(repo, case_id):
    """The review picture for both roles: the submitted versions, the checker's marks, the comments and the trail."""
    case, config = workflow_config(repo, case_id)
    names = {d.id: d.name for d in config.template.sections}
    events = sorted(repo.list_for_case(s.WorkflowEvent, case_id), key=lambda e: (e.created_at, e.id))
    es = repo.get(s.ESVersion, case.active_es_version_id) if case.active_es_version_id else None
    submitted = dict(es.section_versions) if es else {}
    states = {st.section_id: st for st in repo.list_for_case(s.Section, case_id)}
    marks = latest_marks(repo, case_id)
    returned = returned_scope(repo, case_id) if case.workflow_state == 'Returned to CA' else []
    named = events[-1].returned_sections if events and events[-1].action == 'return' and case.workflow_state == 'Returned to CA' else []
    sections = []
    for section_id, name in names.items():
        state, mark = states.get(section_id), marks.get(section_id)
        draft_id = submitted.get(section_id)
        # A mark counts for the version it was made on. While the paper is back with the maker, the last query stays visible.
        on_this_version = bool(mark and mark.status != 'cleared' and mark.draft_id == draft_id)
        sections.append(dict(section_id=section_id, name=name, applicable=bool(state and state.applicable), submitted_draft_id=draft_id,
            mark=mark.model_dump(mode='json') if mark and mark.status != 'cleared' and (on_this_version or mark.status == 'query') else None,
            mark_current=on_this_version,
            changed_since_mark=bool(mark and draft_id and mark.draft_id != draft_id),
            changed_since_submission=bool(state and draft_id and state.current_draft_id != draft_id),
            returned=section_id in named, editable=section_id in returned if case.workflow_state == 'Returned to CA' else case.workflow_state == config.workflow.initial_state))
    to_review = [sec for sec in sections if sec['applicable'] and sec['submitted_draft_id']]
    return dict(case_id=case_id, state=case.workflow_state, active_es_version_id=case.active_es_version_id,
        latest_event_id=events[-1].id if events else None, sections=sections,
        gap_reasons=dict(es.gap_reasons) if es else {},  # reasons recorded with the last submission, offered again on resubmission
        summary=dict(to_review=len(to_review), reviewed=sum(bool(sec['mark_current'] and sec['mark']['status'] == 'reviewed') for sec in to_review),
                     queries=sum(bool(sec['mark_current'] and sec['mark']['status'] == 'query') for sec in to_review)),
        events=[e.model_dump(mode='json') for e in events],
        comments=[c.model_dump(mode='json') for c in sorted(repo.list_for_case(s.Comment, case_id), key=lambda c: (c.created_at, c.id))],
        note='Marks record that a reviewer has read a section. They are not a credit decision.')


def mark(repo, case_id, request):
    case, _ = workflow_config(repo, case_id)
    if REVIEWING.get(request.role) != case.workflow_state:
        raise WorkflowConflict('This role can mark sections only while the ES is with it for review')
    if request.expected_es_version_id != case.active_es_version_id:
        raise WorkflowConflict('The submitted ES changed; reload before marking')
    es = repo.get(s.ESVersion, case.active_es_version_id)
    draft_id = es.section_versions.get(request.section_id)
    if not draft_id:
        raise ValueError('This section is not part of the submitted ES')
    note = request.note.strip()
    if request.status == 'query' and not note:
        raise ValueError('A query needs a note for the maker')
    repo.save(s.ReviewMark(case_id=case_id, section_id=request.section_id, draft_id=draft_id, es_version_id=es.id,
                           reviewer=request.actor, role=request.role, status=request.status, note=note))
    return view(repo, case_id)
