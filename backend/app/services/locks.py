"""Shared working-content policy; immutable review snapshots are separate records."""
from .. import schemas as s
from ..team_config import TeamConfig


class WorkflowConflict(ValueError):
    pass


# Retain the existing section API exception contract.
RevisionConflict = WorkflowConflict


def workflow_config(repo, case_id):
    case = repo.get(s.Case, case_id)
    return case, TeamConfig.model_validate(case.config_snapshot)


def returned_scope(repo, case_id):
    case, config = workflow_config(repo, case_id)
    if case.workflow_state != 'Returned to CA':
        return []
    events = sorted(repo.list_for_case(s.WorkflowEvent, case_id), key=lambda e: (e.created_at, e.id))
    if not events or events[-1].action != 'return':
        return []  # A manually assigned state is not an authorization.
    sections = set(events[-1].returned_sections)
    # New inputs during a return may invalidate another section. Permit its
    # explicit repair so B25 cannot trap a case with stale, uneditable content.
    reviewed = repo.get(s.ESVersion, events[-1].es_version_id)
    sections.update(st.section_id for st in repo.list_for_case(s.Section, case_id)
                    if st.applicable and (st.readiness == 'Stale'
                        or st.current_draft_id != reviewed.section_versions.get(st.section_id)))
    while True:
        expanded = sections | {d.section_id for d in config.dependencies.items
                               if sections.intersection(d.requires + d.freshness_requires)}
        if expanded == sections:
            return sorted(sections)
        sections = expanded


def require_working(repo, case_id, section_id=None, *, intake=False):
    case, config = workflow_config(repo, case_id)
    # Late evidence may flag working content stale without reopening a final ES.
    if intake and case.workflow_state in config.workflow.final_states:
        return
    if case.workflow_state in config.workflow.locked_states or case.workflow_state in config.workflow.final_states:
        raise WorkflowConflict('Working content is locked in this workflow state')
    if case.workflow_state == config.workflow.initial_state:
        return
    if case.workflow_state == 'Returned to CA':
        scope = returned_scope(repo, case_id)
        if scope and (section_id is None or section_id in scope):
            return
        raise WorkflowConflict('Only named returned sections and their dependants can be changed')
    raise WorkflowConflict('Changes require a working case in Draft state or a recorded return')
