"""Offline round trip: read back an ES that was exported to Word and edited there.

The export marks every drafted paragraph with a bookmark naming its draft and its place in it. This module finds
those paragraphs in an uploaded copy, compares the wording with the section as it stands, and offers the changed
wording for the credit analyst to take. Nothing is taken without the analyst choosing it, and a paragraph whose
figures were changed is shown but never taken: figures come from sources and calculations, not from an edited file.
Comments left in Word can be brought in as review threads. Tables are not read back.
"""
from io import BytesIO
from zipfile import BadZipFile, ZipFile
import re
import xml.etree.ElementTree as ET

from pydantic import BaseModel, ConfigDict, Field

from .. import schemas as s
from ..services import threads
from ..services.versions import EditRequest
from ..team_config import TeamConfig
from .export import MARKER
from .spec import load_spec, section_parts

W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
MAX_BYTES = 30 * 1024 * 1024
NUMBERS = r'\d+(?:[.,]\d+)*'
TRAILING_MARKS = re.compile(r'(?:\s*(?:\[\d+\]|\(see section \d+\)))+\s*$')


class ApplyRequest(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    actor: str = Field(min_length=1, max_length=200)
    # section number -> the draft the comparison was made against, and the paragraphs to take
    sections: dict[int, dict] = Field(default_factory=dict)
    comments: list[dict] = Field(default_factory=list, max_length=200)


def xml_part(package, name):
    try:
        data = package.read(name)
    except KeyError:
        return None
    if b'<!DOCTYPE' in data or b'<!ENTITY' in data:
        raise ValueError('This Word file contains definitions that are not read; save it again from Word and retry')
    return ET.fromstring(data)


def paragraph_text(paragraph):
    """The text as it reads with tracked insertions taken and tracked deletions dropped."""
    out = []
    for node in paragraph.iter():
        if node.tag == W + 't':
            out.append(node.text or '')
        elif node.tag in (W + 'tab', W + 'br'):
            out.append(' ')
    return ' '.join(''.join(out).split())


def read(content):
    """Marked paragraphs and Word comments in an uploaded file."""
    if not content or len(content) > MAX_BYTES:
        raise ValueError('The file is empty or larger than 30 MB')
    try:
        package = ZipFile(BytesIO(content))
        document = xml_part(package, 'word/document.xml')
    except BadZipFile:
        raise ValueError('This is not a Word .docx file')
    except ET.ParseError:
        raise ValueError('The Word file could not be read')
    if document is None:
        raise ValueError('This is not a Word .docx file')
    marked, anchors, last = {}, {}, None
    for paragraph in document.iter(W + 'p'):
        names = [n.get(W + 'name', '') for n in paragraph.iter(W + 'bookmarkStart')]
        mine = next((n for n in names if n.startswith(MARKER)), None)
        text = paragraph_text(paragraph)
        if mine and mine not in marked:
            marked[mine] = text
            last = mine
        for start in paragraph.iter(W + 'commentRangeStart'):
            anchors[start.get(W + 'id')] = dict(marker=mine or last, quote=text[:300])
    comments = []
    try:
        notes = xml_part(package, 'word/comments.xml')
    except ET.ParseError:
        notes = None
    for note in (notes.iter(W + 'comment') if notes is not None else []):
        text = ' '.join(filter(None, (paragraph_text(p) for p in note.iter(W + 'p'))))
        anchor = anchors.get(note.get(W + 'id'), {})
        if text:
            comments.append(dict(author=note.get(W + 'author') or 'Unknown', text=text[:3800], marker=anchor.get('marker'), quote=anchor.get('quote') or None))
    return marked, comments


def protected(claim):
    return bool(claim.get('computed_value_id') or claim.get('computed_value_ids') or claim.get('internal_rating') or claim.get('requires_unsecured_confirmation')
                or claim.get('kind') in {'computed_summary', 'case_input', 'ca_position', 'ca_input'})


def compare(service, case_id, content):
    """What the uploaded file changes, section by section. Reads only; nothing is saved."""
    marked, comments = read(content)
    if not marked:
        raise ValueError('No paragraph markers were found. Export the ES again from this app and edit that copy; '
                         'a file exported before markers were added, or one rebuilt by copy and paste, cannot be matched back.')
    by_draft = {}
    for name, text in marked.items():
        draft_hex, _, position = name[len(MARKER):].rpartition('_')
        if len(draft_hex) == 32 and position.isdigit():
            by_draft.setdefault(draft_hex, {})[int(position)] = text
    states = service.sections(case_id)
    case = service.repo.get(s.Case, case_id)
    config_names = {d.id: d.name for d in TeamConfig.model_validate(case.config_snapshot).template.sections}
    spec = load_spec(case.team_id)
    sections, section_of = [], {}
    known = set()
    for state in states:
        if not state.current_draft_id:
            continue
        draft_hex = state.current_draft_id.replace('-', '')
        known.add(draft_hex)
        section_of[draft_hex] = state.section_id
        found = by_draft.get(draft_hex)
        if found is None:
            continue
        draft = service.repo.get(s.DraftVersion, state.current_draft_id)
        claims = draft.claim_spans[1:]
        titles = {p['key']: p.get('title') or p['key'] for p in section_parts(spec, state.section_id)} if spec else {}
        changes, same = [], 0
        for position, claim in enumerate(claims):
            if position not in found:
                continue
            before = ' '.join(claim['text'].split())
            after = TRAILING_MARKS.sub('', found[position]).strip()
            if after == before:
                same += 1
                continue
            kind, reason = 'wording', None
            if not after:
                kind, reason = 'removed', 'The paragraph was emptied in Word. Remove wording in the section itself.'
            elif protected(claim):
                kind, reason = 'protected', 'This wording is supplied or calculated by the system and is changed through its own input.'
            elif re.findall(NUMBERS, after) != re.findall(NUMBERS, before):
                kind, reason = 'figures', 'A figure was changed. Figures come from the sources and the calculations, so this is not taken from the Word file.'
            changes.append(dict(claim_id=claim['id'], part=titles.get(claim.get('part')) or claim.get('part'), kind=kind, reason=reason, before=before, after=after))
        sections.append(dict(section_id=state.section_id, name=config_names.get(state.section_id), draft_id=state.current_draft_id,
                             changes=changes, unchanged=same))
    # Markers of drafts that are no longer current: the section changed in the app after the file was exported.
    stale_drafts = set(by_draft) - known
    stale = set()
    if stale_drafts:
        for draft in service.repo.list_for_case(s.DraftVersion, case_id):
            if draft.id.replace('-', '') in stale_drafts:
                stale.add(draft.section_id)
                section_of[draft.id.replace('-', '')] = draft.section_id
    foreign = len([d for d in stale_drafts if d not in section_of])
    if foreign and not sections and not stale:
        raise ValueError('This file was exported from a different paper')
    notes = [dict(author=c['author'], text=c['text'], quote=c['quote'],
                  section_id=section_of.get(c['marker'][len(MARKER):].rpartition('_')[0]) if c['marker'] else None) for c in comments]
    return dict(sections=sections, stale_sections=sorted(stale), comments=notes, paragraphs_found=len(marked),
                note='Wording you take is saved as a new version of its section, marked as edited by the credit analyst. Tables are not read back from Word.')


def apply(service, case_id, request):
    """Save the chosen wording as new section versions, and bring the chosen Word comments in as review threads."""
    states = {state.section_id: state for state in service.sections(case_id)}
    saved, opened = [], 0
    for section_id, chosen in request.sections.items():
        state = states.get(section_id)
        replacements = chosen.get('replacements') or {}
        if not replacements:
            continue
        if not state or state.current_draft_id != chosen.get('draft_id'):
            raise ValueError(f'Section {section_id} changed after the file was compared; upload the file again')
        service.save(case_id, section_id, EditRequest(actor=request.actor, expected_draft_id=state.current_draft_id,
                     expected_revision=state.editor_revision, expected_input_fingerprint=state.input_fingerprint, replacements=replacements))
        saved.append(section_id)
    for comment in request.comments:
        if comment.get('section_id') not in states or not str(comment.get('text') or '').strip():
            continue
        threads.open_thread(service.repo, case_id, threads.OpenRequest(actor=request.actor, role='CA', section_id=comment['section_id'],
            quote=(comment.get('quote') or None), text=f"Comment left in Word by {comment.get('author') or 'Unknown'}: {comment['text']}"[:4000]))
        opened += 1
    return dict(saved_sections=saved, threads_opened=opened)
