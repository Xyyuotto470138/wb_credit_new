"""Review threads: comments between the roles on a section or one part of it.

A thread is talk about the ES, not part of it. Opening, replying, resolving and reopening change no section, no
version and no workflow state, so they are allowed at every stage, including while the ES is with a reviewer.
"""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .. import schemas as s
from ..es2.spec import load_spec, section_parts

Commenter = Literal['CA', 'Credit Head', 'Credit Approver']


class Said(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    actor: str = Field(min_length=1, max_length=200)
    role: Commenter
    text: str = Field(min_length=1, max_length=4000)


class OpenRequest(Said):
    section_id: int
    part_key: str | None = Field(default=None, min_length=1, max_length=200)
    quote: str | None = Field(default=None, min_length=1, max_length=2000)


class ResolveRequest(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    actor: str = Field(min_length=1, max_length=200)
    role: Commenter
    conclusion: str = Field(min_length=1, max_length=4000)


class ReopenRequest(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    actor: str = Field(min_length=1, max_length=200)
    role: Commenter


def entry(request, text):
    return dict(author=request.actor, role=request.role, text=text, at=s.utcnow().isoformat())


def listing(repo, case_id):
    threads = sorted(repo.list_for_case(s.CommentThread, case_id), key=lambda t: (t.created_at, t.id))
    return [t.model_dump(mode='json') for t in threads]


def open_count(repo, case_id):
    return sum(t.status == 'open' for t in repo.list_for_case(s.CommentThread, case_id))


def held(repo, case_id, thread_id):
    try:
        thread = repo.get(s.CommentThread, thread_id)
    except ValueError:
        raise ValueError('Comment thread not found')
    if thread.case_id != case_id:
        raise ValueError('Comment thread not found')
    return thread


def open_thread(repo, case_id, request):
    case = repo.get(s.Case, case_id)
    title = None
    if request.part_key:
        spec = load_spec(case.team_id)
        try:
            part = next(p for p in section_parts(spec, request.section_id) if p['key'] == request.part_key) if spec else None
        except StopIteration:
            part = None
        if not part:
            raise ValueError('That part is not in this section')
        title = part.get('title') or request.part_key
    return repo.save(s.CommentThread(case_id=case_id, section_id=request.section_id, part_key=request.part_key, part_title=title,
                                     quote=request.quote, comments=[entry(request, request.text)])).model_dump(mode='json')


def reply(repo, case_id, thread_id, request):
    thread = held(repo, case_id, thread_id)
    if thread.status != 'open':
        raise ValueError('This thread is resolved; reopen it to reply')
    return repo.save(thread.model_copy(update=dict(comments=[*thread.comments, entry(request, request.text)]))).model_dump(mode='json')


def resolve(repo, case_id, thread_id, request):
    thread = held(repo, case_id, thread_id)
    if thread.status != 'open':
        raise ValueError('This thread is already resolved')
    return repo.save(thread.model_copy(update=dict(status='resolved', conclusion=request.conclusion, resolved_by=request.actor,
                                                    resolved_role=request.role, resolved_at=s.utcnow()))).model_dump(mode='json')


def reopen(repo, case_id, thread_id, request):
    thread = held(repo, case_id, thread_id)
    if thread.status != 'resolved':
        raise ValueError('This thread is already open')
    note = dict(author=request.actor, role=request.role, at=s.utcnow().isoformat(), reopened=True,
                text=f'Reopened. Earlier conclusion by {thread.resolved_by}: {thread.conclusion}')
    return repo.save(thread.model_copy(update=dict(status='open', conclusion=None, resolved_by=None, resolved_role=None, resolved_at=None,
                                                    comments=[*thread.comments, note]))).model_dump(mode='json')
