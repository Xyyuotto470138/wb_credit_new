"""Offline, shared intake. Content is data, never instructions to a provider.

Caller owns the database transaction; serialize writes (BEGIN IMMEDIATE on
SQLite). Original bytes and classification observations are immutable. B05
refreshes expected inputs and section readiness; draft versions remain unchanged.
"""
from calendar import monthrange
from datetime import date
from email import policy
from email.parser import BytesParser
from hashlib import sha256
from io import BytesIO
import os
from pathlib import Path
import re
import stat
from typing import Literal
import xml.etree.ElementTree as ET
from zipfile import ZipFile

import fitz
import openpyxl
from pydantic import BaseModel, ConfigDict, Field, model_validator

from .locks import require_working
from .. import schemas
from ..repository import Repository
from ..team_config import TeamConfig

MAX_BYTES = 25 * 1024 * 1024
MAX_TEXT = 200_000
MAX_ARCHIVE_BYTES = 100 * 1024 * 1024
SUPPORTED = {'.pdf', '.docx', '.xlsx', '.txt', '.csv', '.eml'}


class IntakeError(ValueError):
    """A request cannot safely be ingested; no document is created."""


class Metadata(BaseModel):
    """User-supplied classification hints, retained as such, never confirmation."""
    model_config = ConfigDict(extra='forbid')
    catalogue_id: int | None = Field(default=None, ge=1)
    suggestion_id: str | None = None
    entity: str | None = Field(default=None, min_length=1, max_length=300)
    period: str | None = Field(default=None, min_length=1, max_length=100)
    synthetic: bool = False
    scope: str = Field(default='default', min_length=1, max_length=300)

    @model_validator(mode='after')
    def one_type(self):
        if self.catalogue_id is not None and self.suggestion_id is not None:
            raise ValueError('Supply a catalogue type or suggestion, not both')
        if self.period and period_key(self.period) is None:
            raise ValueError('Period must be ISO date, YYYY, FYyyyy or yyyy-Qn')
        return self


class IntakeResult(BaseModel):
    outcome: Literal['created', 'duplicate', 'rejected']
    filename: str
    document: schemas.Document | None = None
    explanations: list[str] = Field(default_factory=list)


# Questions about a file that the credit analyst's own review answers.
ANALYST_SETTLES = {'unknown_type', 'type_mismatch', 'rating_scope', 'unknown_entity', 'wrong_entity', 'entity_mismatch', 'unknown_period', 'period_mismatch'}


def normalize(value):
    return ' '.join(re.findall(r'[a-z0-9]+', value.casefold()))


def type_words(value):
    return re.sub(r'\b(reports|statements)\b', lambda match: match[0][:-1], normalize(value))


def period_key(value):
    if not value:
        return None
    value = value.strip().upper()
    try:
        if re.fullmatch(r'(FY)?\d{4}', value):
            return date(int(value[-4:]), 12, 31)
        match = re.fullmatch(r'(\d{4})-Q([1-4])', value)
        if match:
            year, quarter = map(int, match.groups())
            month = quarter * 3
            return date(year, month, monthrange(year, month)[1])
        return date.fromisoformat(value)
    except ValueError:
        return None


def safe_filename(filename):
    # Reject traversal rather than silently reinterpret caller input.
    if not filename or len(filename) > 240 or filename in {'.', '..'} or any(c in filename for c in '/\\\x00') or any(ord(c) < 32 for c in filename):
        raise IntakeError('Provide a plain filename without path components')
    return filename


def archive_guard(content, required):
    with ZipFile(BytesIO(content)) as archive:
        entries = archive.infolist()
        if len(entries) > 5000 or sum(e.file_size for e in entries) > MAX_ARCHIVE_BYTES:
            raise IntakeError('Office archive exceeds extraction limits')
        if required not in archive.namelist():
            raise IntakeError('Content does not match the named Office format')
        # Never resolve external relationships or execute macros/embedded code.
        if any(e.filename.lower().endswith('vbaproject.bin') for e in entries):
            raise IntakeError('Macro-enabled content is unsupported')


def preview(content, suffix):
    """Bounded classification preview, not B08's page evidence index."""
    if suffix == '.pdf':
        if not content.startswith(b'%PDF-'):
            raise IntakeError('Content does not match PDF filename')
        with fitz.open(stream=content, filetype='pdf') as pdf:
            if pdf.needs_pass:
                raise IntakeError('Encrypted PDF requires an unlocked copy')
            return '\n'.join(pdf[i].get_text()[:MAX_TEXT // 3] for i in range(min(3, len(pdf))))[:MAX_TEXT]
    if suffix == '.docx':
        archive_guard(content, 'word/document.xml')
        with ZipFile(BytesIO(content)) as archive:
            names = ['word/document.xml'] + sorted(n for n in archive.namelist() if re.fullmatch(r'word/header\d+\.xml', n))
            paragraphs = []
            for name in names:
                raw = archive.read(name)
                if b'<!DOCTYPE' in raw.upper() or b'<!ENTITY' in raw.upper():
                    raise IntakeError('Unsupported XML declaration')
                root = ET.fromstring(raw)
                ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
                paragraphs.extend(''.join(p.itertext()) for p in root.findall('.//w:p', ns))
            return '\n'.join(paragraphs)[:MAX_TEXT]
    if suffix == '.xlsx':
        archive_guard(content, 'xl/workbook.xml')
        workbook = openpyxl.load_workbook(BytesIO(content), read_only=True, data_only=True, keep_links=False)
        try:
            return '\n'.join(' | '.join(str(v) for v in row if v is not None)
                             for sheet in workbook.worksheets[:3]
                             for row in sheet.iter_rows(max_row=30, max_col=20, values_only=True))[:MAX_TEXT]
        finally:
            workbook.close()
    if suffix == '.eml':
        message = BytesParser(policy=policy.default).parsebytes(content)
        body = message.get_body(preferencelist=('plain',))
        if body is None:
            return ''
        return (str(message.get('Subject', '')) + '\n' + body.get_content())[:MAX_TEXT]
    text = content.decode('utf-8-sig')
    if '\x00' in text:
        raise IntakeError('Binary content does not match a text filename')
    return text[:MAX_TEXT]


def classify(text, filename, case, config, metadata):
    issues = []
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    # Only title/filename matching: references later in the text are not types.
    titles = [line for line in lines[:4] if not line.upper().startswith('SYNTHETIC DEMO DATA')]
    title = type_words(' '.join(titles[:1]) + ' ' + Path(filename).stem)
    candidates = []
    for item in config.catalogue.items:
        terms = [item.name.split('(')[0].strip(), *re.findall(r'\(([^)]+)\)', item.name)]
        if any(type_words(term) and f' {type_words(term)} ' in f' {title} ' for term in terms):
            candidates.append(item.id)
    catalogue_id = metadata.catalogue_id
    suggestion_id = metadata.suggestion_id
    if catalogue_id is None and suggestion_id is None and len(candidates) == 1:
        catalogue_id = candidates[0]
    elif catalogue_id is not None and candidates and catalogue_id not in candidates:
        issues.append('type_mismatch: Supplied type differs from the title; review classification.')
    if catalogue_id is None and suggestion_id is None:
        issues.append('unknown_type: Document type needs manual classification.')
    selected_type = next((i for i in config.catalogue.items if i.id == catalogue_id), None)
    if selected_type and selected_type.public_support == 'external only' and 'internal' not in title.split():
        issues.append('rating_scope: Internal rating scope is not established by the title; external ratings cannot satisfy the internal rating input.')

    match = re.search(r'(?im)^\s*(?:borrower|entity)\s*:\s*([^|\n]+)', text)
    observed_entity = match.group(1).strip() if match else None
    if observed_entity is None:
        # Only a header/name cell is an identity signal. A reference to the
        # borrower deep inside another entity's report is not a match.
        if any(normalize(line.split('|')[0]) == normalize(case.borrower_name) for line in lines[:12]):
            observed_entity = case.borrower_name
    entity = observed_entity or metadata.entity or ''
    if observed_entity and metadata.entity and normalize(observed_entity) != normalize(metadata.entity):
        issues.append('entity_mismatch: Supplied entity differs from the document label.')
    if not entity:
        issues.append('unknown_entity: Borrower identity needs manual review.')
    elif normalize(entity) != normalize(case.borrower_name):
        issues.append('wrong_entity: Document entity differs from this case borrower.')

    observed_period = None
    period_header = '\n'.join(line for line in lines[:12]
                              if not re.match(r'(prior|previous|supersedes|source|public source)\b', line, re.I))
    for pattern in (
        r'valuation effective\s+(\d{4}-\d{2}-\d{2})',
        r'(?im)^\s*(?:period|as of|report date)\s*:\s*((?:FY)?\d{4}(?:-\d{2}-\d{2}|-Q[1-4])?)\s*$',
        r'\b(?:dated|as of)\s+(\d{4}-\d{2}-\d{2})',
        r'\b(FY\d{4})\b',
    ):
        match = re.search(pattern, period_header, re.I)
        if match and period_key(match.group(1)):
            observed_period = match.group(1).upper()
            break
    period = metadata.period or observed_period
    if not period:
        issues.append('unknown_period: Reporting period needs manual review.')
    elif observed_period and metadata.period and period_key(observed_period) != period_key(metadata.period):
        issues.append('period_mismatch: Supplied period differs from the detected document period.')
    if not text.strip():
        issues.append('no_text: No usable text extracted; provide a readable copy or manual review (OCR unavailable).')
    return catalogue_id, suggestion_id, entity, period, issues, {
        'type_candidates': candidates, 'entity': observed_entity, 'period': observed_period,
    }


class IntakeService:
    def __init__(self, repository: Repository, storage_root: Path, folders=None, max_bytes=MAX_BYTES):
        self.repository = repository
        self.storage_root = Path(storage_root).resolve()
        # Folder IDs are operator configuration, never request-supplied paths.
        self.folders = {key: Path(value).absolute() for key, value in (folders or {}).items()}
        self.max_bytes = max_bytes

    def ingest(self, case_id, filename, content, *, origin='upload', metadata=None, reviewed_by=None, held_id=None):
        require_working(self.repository, case_id, intake=True)
        safe_filename(filename)
        if origin not in {'upload', 'folder'}:
            raise IntakeError('This intake route accepts upload or folder provenance only')
        if not content or len(content) > self.max_bytes:
            raise IntakeError('File is empty or exceeds the intake byte limit')
        case = self.repository.get(schemas.Case, case_id)
        metadata = Metadata.model_validate(metadata or {})
        config = TeamConfig.model_validate(case.config_snapshot)
        if metadata.catalogue_id is not None and metadata.catalogue_id not in {i.id for i in config.catalogue.items}:
            raise IntakeError('Unknown configured catalogue type')
        if metadata.suggestion_id is not None and metadata.suggestion_id not in {i.id for i in config.rules.suggestions}:
            raise IntakeError('Unknown configured suggestion')
        digest = sha256(content).hexdigest()
        documents = self.repository.list_for_case(schemas.Document, case_id)
        # A file the analyst set aside, or classified again, no longer stands in for its content.
        duplicate = next((d for d in documents if d.content_hash == digest and d.conflict_status != 'rejected'), None)
        if duplicate:
            # Do not let a new name, route or hints mutate historical provenance.
            stored = Path(duplicate.storage_path)
            if not stored.is_file() or stored.is_symlink() or sha256(stored.read_bytes()).hexdigest() != digest:
                raise IntakeError('Stored content failed integrity validation; restore the original blob before retrying')
            self._refresh(case_id)
            return IntakeResult(outcome='duplicate', filename=filename, document=duplicate,
                                explanations=['Identical content already held for this case; existing version and classification retained.', *duplicate.intake.get('issues', [])])
        suffix = Path(filename).suffix.lower()
        extraction_issues = []
        text = ''
        if suffix not in SUPPORTED:
            extraction_issues.append('unsupported_format: File retained for manual review; readable PDF, DOCX, XLSX, EML, CSV or TXT needed.')
        else:
            try:
                text = preview(content, suffix)
            except Exception as error:
                # Parser errors are evidence gaps, not 500s or a claim of no document.
                reason = str(error) if isinstance(error, IntakeError) else 'Cannot decode this file safely'
                extraction_issues.append(f'unreadable: {reason}; manual review required.')
        catalogue_id, suggestion_id, entity, period, issues, observed = classify(text, filename, case, config, metadata)
        issues = extraction_issues + issues
        overridden = []
        if reviewed_by:
            # The credit analyst has looked at the file and stated its type, date and that it is this borrower's.
            # That review settles the questions the classifier could not; unreadable files and date clashes still hold.
            catalogue_id, suggestion_id, entity, period = metadata.catalogue_id, metadata.suggestion_id, case.borrower_name, metadata.period
            overridden = [i for i in issues if i.split(':')[0] in ANALYST_SETTLES]
            issues = [i for i in issues if i not in overridden]
        stream = [d for d in documents if (d.catalogue_id, d.suggestion_id, normalize(d.entity), d.intake.get('scope', 'default')) ==
                  (catalogue_id, suggestion_id, normalize(entity), metadata.scope)]
        accepted = [d for d in stream if d.conflict_status in {'none', 'accepted'} and period_key(d.period)]
        previous = max(accepted, key=lambda d: (period_key(d.period), d.revision, d.created_at), default=None)
        if previous and period_key(period):
            if period_key(period) < period_key(previous.period):
                issues.append('older_period: An accepted newer period is already held; this file does not replace it.')
            elif period_key(period) == period_key(previous.period):
                issues.append('same_period_changed: Different content for the same period requires review before replacement.')
        relative = Path(digest[:2]) / digest
        destination = self.storage_root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        # Store before the DB row. Rollback can leave an unreferenced hash blob,
        # safely reusable on retry; never delete bytes another transaction may use.
        try:
            with destination.open('xb') as output:
                output.write(content)
        except FileExistsError:
            if destination.is_symlink() or sha256(destination.read_bytes()).hexdigest() != digest:
                raise IntakeError('Stored content failed integrity validation')
        document = self.repository.save(schemas.Document(
            case_id=case_id, catalogue_id=catalogue_id, suggestion_id=suggestion_id,
            entity=entity, period=period, content_hash=digest, storage_path=str(destination),
            revision=max((d.revision for d in stream), default=0) + 1,
            supersedes_id=previous.id if previous and not issues else None,
            origin=origin, synthetic=metadata.synthetic or 'SYNTHETIC DEMO DATA' in text.upper(),
            original_filename=filename, conflict_status='pending' if issues else 'none',
            intake={'classifier': 'deterministic-v1', 'scope': metadata.scope,
                    'status': 'manual_review' if issues else 'classified', 'issues': issues,
                    'supplied': metadata.model_dump(mode='json'), 'observed': observed,
                    'compared_document_id': previous.id if previous else None,
                    **({'review': {'by': reviewed_by, 'settled': overridden, 'held_document_id': held_id}} if reviewed_by else {})},
        ))
        if case.first_upload_at is None:
            self.repository.save(case.model_copy(update={'first_upload_at': document.created_at}))
        self._refresh(case_id)
        return IntakeResult(outcome='created', filename=filename, document=document,
                            explanations=issues or ['New immutable document version stored; classification is not CA confirmation.'])

    def _held(self, case_id, document_id):
        require_working(self.repository, case_id, intake=True)
        try:
            document = self.repository.get(schemas.Document, document_id)
        except ValueError:
            raise IntakeError('Document not found')
        if document.case_id != case_id:
            raise IntakeError('Document not found')
        if document.conflict_status != 'pending':
            raise IntakeError('This file is not waiting for review')
        return document

    def classify_held(self, case_id, document_id, *, actor, period, catalogue_id=None, suggestion_id=None):
        """The analyst states what a held file is. The held record is closed and the file is stored again under that
        classification, so the original observation is kept as it was."""
        document = self._held(case_id, document_id)
        if not actor.strip() or (catalogue_id is None) == (suggestion_id is None) or not period:
            raise IntakeError('Give your name, one document type and the document date')
        stored = Path(document.storage_path)
        if not stored.is_file() or stored.is_symlink() or sha256(stored.read_bytes()).hexdigest() != document.content_hash:
            raise IntakeError('Stored content failed integrity validation; upload the file again')
        case = self.repository.get(schemas.Case, case_id)
        metadata = Metadata(catalogue_id=catalogue_id, suggestion_id=suggestion_id, entity=case.borrower_name, period=period,
                            synthetic=document.synthetic, scope=document.intake.get('scope', 'default'))
        self.repository.save(document.model_copy(update={'conflict_status': 'rejected'}))
        return self.ingest(case_id, document.original_filename, stored.read_bytes(),
                           origin=document.origin if document.origin in {'upload', 'folder'} else 'upload', metadata=metadata, reviewed_by=actor.strip(), held_id=document.id)

    def set_aside(self, case_id, document_id):
        """The analyst decides a held file is not for this paper. It is kept in the store and used nowhere."""
        document = self.repository.save(self._held(case_id, document_id).model_copy(update={'conflict_status': 'rejected'}))
        self._refresh(case_id)
        return document

    def _refresh(self, case_id):
        # Lazy import avoids a cycle: readiness shares the intake identity normalizer.
        from .readiness import ReadinessService
        ReadinessService(self.repository).refresh(case_id)

    def scan(self, case_id, folder_id, metadata_by_path=None):
        require_working(self.repository, case_id, intake=True)
        self.repository.get(schemas.Case, case_id)
        if folder_id not in self.folders:
            raise IntakeError('Unknown configured folder ID')
        root = self.folders[folder_id]
        if root.is_symlink() or root.resolve() != root or not root.is_dir():
            raise IntakeError('Configured folder must be an existing directory without symlinks')
        if root == self.storage_root or root in self.storage_root.parents or self.storage_root in root.parents:
            raise IntakeError('Intake folder and content storage must be separate')
        results = []
        metadata_by_path = metadata_by_path or {}
        # No background watcher; deterministic, recursive and bounded per request.
        for current, directories, filenames in os.walk(root, followlinks=False):
            directories.sort()
            filenames.sort()
            for name in list(directories):
                path = Path(current) / name
                if name.startswith('.') or path.is_symlink():
                    directories.remove(name)
                    if path.is_symlink():
                        results.append(IntakeResult(outcome='rejected', filename=path.relative_to(root).as_posix(),
                                                    explanations=['Symlink directory is not scanned']))
            for name in filenames:
                if name.startswith('.'):
                    continue
                path = Path(current) / name
                relative = path.relative_to(root).as_posix()
                if len(results) >= 500:
                    raise IntakeError('Folder exceeds 500 files; split the intake folder')
                try:
                    # O_NOFOLLOW plus fstat rejects links, devices and FIFOs before reading.
                    if path.resolve().parent != Path(current).resolve() or path.is_symlink():
                        raise IntakeError('Symlink file is not scanned')
                    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
                    with os.fdopen(descriptor, 'rb') as source:
                        info = os.fstat(source.fileno())
                        if not stat.S_ISREG(info.st_mode):
                            raise IntakeError('Only regular files are scanned')
                        if info.st_size > self.max_bytes:
                            raise IntakeError('File exceeds the intake byte limit')
                        content = source.read(self.max_bytes + 1)
                    result = self.ingest(case_id, name, content, origin='folder', metadata=metadata_by_path.get(relative))
                    results.append(result.model_copy(update={'filename': relative}))
                except (OSError, ValueError) as error:
                    reason = str(error) if isinstance(error, IntakeError) else 'File or classification metadata could not be read; review the input.'
                    results.append(IntakeResult(outcome='rejected', filename=relative, explanations=[reason]))
        self._refresh(case_id)
        return results
