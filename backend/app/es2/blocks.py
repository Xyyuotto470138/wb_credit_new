"""Analyst added content: text, a pasted table or a screenshot placed anywhere in a specification-driven section.

A block belongs to the analyst. It is kept exactly as supplied, labelled as analyst added, never checked or
changed by the system, and carried across redrafts. Every change is saved as a new version of the section.
"""
from base64 import b64decode
from binascii import Error as DecodeError
from copy import deepcopy
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from typing import Literal
from uuid import uuid4
import re

from PIL import Image
from pydantic import BaseModel, ConfigDict, Field, model_validator

from .. import schemas as s
from ..services.versions import VersionRequest, VersionService
from .spec import load_spec, section_parts

LABEL = 'Analyst added. Not checked by the system.'
MAX_BLOCKS, MAX_ROWS, MAX_COLUMNS, MAX_CELL, MAX_IMAGE_BYTES = 30, 80, 14, 600, 8 * 1024 * 1024
IMAGE_NAME = re.compile(r'^[0-9a-f]{64}\.(png|jpg)$')
CONTROL = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f]')
clean = lambda text: CONTROL.sub('', str(text)).replace('\r\n', '\n').replace('\r', '\n')


class BlockRequest(VersionRequest):
    model_config = ConfigDict(extra='forbid')
    op: Literal['add', 'update', 'delete', 'move']
    block_id: str | None = None
    kind: Literal['text', 'table', 'image'] | None = None
    after: str | None = Field(default=None, max_length=100)  # part key the block follows; '' is the top of the section
    title: str | None = Field(default=None, max_length=200)
    text: str | None = Field(default=None, max_length=20000)
    rows: list[list[str]] | None = None
    header: bool = True
    image_data: str | None = None  # base64 PNG or JPEG
    direction: Literal['up', 'down'] | None = None

    @model_validator(mode='after')
    def shape(self):
        if self.op != 'add' and not self.block_id:
            raise ValueError('Name the block to change')
        if self.op == 'add' and (self.kind is None or self.after is None):
            raise ValueError('A new block needs a kind and a position')
        if self.op == 'move' and not self.direction:
            raise ValueError('A move needs a direction')
        return self


def table_rows(rows):
    if not rows or len(rows) > MAX_ROWS or not any(str(cell).strip() for row in rows for cell in row):
        raise ValueError(f'A table needs between 1 and {MAX_ROWS} rows with some content')
    width = max(len(row) for row in rows)
    if not 1 <= width <= MAX_COLUMNS:
        raise ValueError(f'A table can have up to {MAX_COLUMNS} columns')
    return [[clean(cell).strip()[:MAX_CELL] for cell in row] + [''] * (width - len(row)) for row in rows]


def store_image(storage_root, case_id, data):
    """Save a pasted PNG or JPEG under the case's own folder, named by its hash. Returns (name, width, height)."""
    try:
        raw = b64decode(data.split(',', 1)[-1], validate=True)
    except (DecodeError, ValueError) as error:
        raise ValueError('The image could not be read') from error
    if not raw or len(raw) > MAX_IMAGE_BYTES:
        raise ValueError('An image can be up to 8 MB')
    try:
        with Image.open(BytesIO(raw)) as image:
            kind, size = image.format, image.size
            image.verify()
    except Exception as error:
        raise ValueError('Only PNG and JPEG images can be added') from error
    if kind not in ('PNG', 'JPEG'):
        raise ValueError('Only PNG and JPEG images can be added')
    name = sha256(raw).hexdigest() + ('.png' if kind == 'PNG' else '.jpg')
    folder = Path(storage_root) / 'blocks' / case_id
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / name
    if not target.exists():
        target.write_bytes(raw)
    return name, size[0], size[1]


def image_path(storage_root, case_id, name):
    if not IMAGE_NAME.match(name or ''):
        raise ValueError('Unknown image')
    folder = (Path(storage_root) / 'blocks' / case_id).resolve()
    target = (folder / name).resolve()
    if target.parent != folder or not target.is_file():
        raise ValueError('Unknown image')
    return target


def anchors(case, section_id):
    spec = load_spec(case.team_id)
    if not spec:
        raise ValueError('Analyst added content is available on sections drafted from the ES specification')
    return [''] + [part['key'] for part in section_parts(spec, section_id) if not part.get('hidden')]


def ordered(blocks, keys):
    """Blocks in reading order: by the part they follow, then as placed. A block whose part has gone sits at the end."""
    place = {key: i for i, key in enumerate(keys)}
    return sorted(blocks, key=lambda b: place.get(b['after'], len(keys)))


def blocks_text(blocks):
    """Plain text of the blocks, for sections that read this one."""
    out = []
    for block in blocks:
        head = f"Analyst added {block['kind']}" + (f": {block['title']}" if block.get('title') else '')
        body = block.get('text', '') if block['kind'] == 'text' else '\n'.join(' | '.join(row) for row in block.get('rows', [])) if block['kind'] == 'table' else '[image]'
        out.append(f'{head}\n{body}')
    return '\n\n'.join(out)


def apply(service: VersionService, storage_root, case_id, section_id, request: BlockRequest):
    state, parent = service.prepare(case_id, section_id, request)
    envelope = parent.claim_spans[0] if parent.claim_spans else {}
    if envelope.get('parts') is None:
        raise ValueError('Analyst added content is available on sections drafted from the ES specification')
    case = service.repo.get(s.Case, case_id)
    keys = anchors(case, section_id)
    blocks = deepcopy(envelope.get('blocks') or [])
    now = s.utcnow().isoformat()
    found = next((b for b in blocks if b['id'] == request.block_id), None)
    if request.op != 'add' and not found:
        raise ValueError('Unknown block')

    def content(block):
        if request.title is not None:
            block['title'] = clean(request.title).strip()
        if block['kind'] == 'text' and (request.text is not None or request.op == 'add'):
            text = clean(request.text or '').strip()
            if not text:
                raise ValueError('Text cannot be empty')
            block['text'] = text
        if block['kind'] == 'table' and (request.rows is not None or request.op == 'add'):
            block['rows'], block['header'] = table_rows(request.rows), request.header
        if block['kind'] == 'image' and request.op == 'add':
            if not request.image_data:
                raise ValueError('No image supplied')
            block['image'], block['width'], block['height'] = store_image(storage_root, case_id, request.image_data)

    if request.op == 'add':
        if len(blocks) >= MAX_BLOCKS:
            raise ValueError(f'A section can hold up to {MAX_BLOCKS} added blocks')
        if request.after not in keys:
            raise ValueError('Unknown position in this section')
        block = dict(id=str(uuid4()), kind=request.kind, after=request.after, title='', author=request.actor, created_at=now, label=LABEL)
        content(block)
        blocks.append(block)
    elif request.op == 'update':
        content(found)
        found.update(updated_by=request.actor, updated_at=now)
    elif request.op == 'delete':
        blocks.remove(found)
    else:
        blocks = ordered(blocks, keys)
        index = blocks.index(found)
        step = -1 if request.direction == 'up' else 1
        neighbour = blocks[index + step] if 0 <= index + step < len(blocks) else None
        position = keys.index(found['after']) if found['after'] in keys else len(keys) - 1
        if neighbour and neighbour['after'] == found['after']:
            blocks[index], blocks[index + step] = neighbour, found  # swap within the same position
        elif 0 <= position + step < len(keys):
            found['after'] = keys[position + step]
            blocks.remove(found)
            same = [i for i, b in enumerate(blocks) if b['after'] == found['after']]
            # Moving up lands below what already sits there; moving down lands above it.
            blocks.insert((same[-1] + 1) if same and step < 0 else same[0] if same else len(blocks), found)
        else:
            raise ValueError('The block is already at the edge of the section')
    blocks = ordered(blocks, keys)
    spans = deepcopy(parent.claim_spans)
    spans[0]['blocks'] = blocks
    draft = service.repo.save(s.DraftVersion.model_validate(parent.model_dump() | dict(
        id=str(uuid4()), created_at=s.utcnow(), parent_id=parent.id, claim_spans=spans, ca_edits=True, author=request.actor)))
    for i, claim in enumerate(spans[1:]):
        for ref in claim.get('evidence_ids', []):
            service.repo.save(s.Citation(case_id=case_id, draft_id=draft.id, evidence_id=ref, claim_or_cell=f'claim:{i}:{claim["id"]}'))
    service.repo.save(state.model_copy(update=dict(current_draft_id=draft.id, confirmed_draft_id=None,
        readiness='Stale' if state.readiness == 'Stale' else 'Drafted', editor_revision=state.editor_revision + 1)))
    service.sections(case_id)
    return service.drafting.get(case_id, draft.id)
