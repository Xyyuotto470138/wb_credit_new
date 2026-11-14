"""B07 read model. The persisted readiness services remain authoritative."""
from collections import Counter
from hashlib import sha256
from pathlib import Path
from urllib.parse import quote

import fitz
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from sqlalchemy import select

from .. import models, schemas as s
from ..llm.registry import load_registry
from ..repository import Repository
from ..services.gaps import GapService, current_documents, key
from ..services.intake import MAX_BYTES
from ..services.readiness import ReadinessService
from ..services.search import generation_offers


def dashboard_router(sessions=None, storage_root=None, *, folders=None, intake_presets=None, search_mode='off', demo_case_ids=(), demo_spread_available=False):
    router = APIRouter(tags=['intake dashboard'])

    def require_sessions():
        if sessions is None:
            raise HTTPException(503, 'Case persistence is not configured')

    def case_for(repo, case_id):
        try:
            return repo.get(s.Case, case_id)
        except ValueError:
            raise HTTPException(404, 'Case not found')

    @router.get('/cases')
    def cases():
        require_sessions()
        with sessions() as session:
            rows = session.scalars(select(models.Case).order_by(models.Case.created_at)).all()
            return [dict(id=c.id, borrower_name=c.borrower_name, case_type=c.case_type,
                         team_id=c.team_id, workflow_state=c.workflow_state) for c in rows]

    WITH = {'Draft': 'Credit analyst', 'Returned to CA': 'Credit analyst', 'Question to CA': 'Credit analyst', 'Submitted to Credit Head': 'Credit Head',
            'Supported': 'Credit Head', 'With Credit Approver': 'Credit Approver'}

    @router.get('/papers')
    def papers():
        """Every paper in the store with where it stands, for the papers list. Read from the same services as the workbench."""
        require_sessions()
        from ..es2 import sense
        from ..services.locks import returned_scope
        with sessions() as session:
            session.connection().exec_driver_sql('BEGIN IMMEDIATE')
            repo = Repository(session)
            result = []
            for row in session.scalars(select(models.Case).order_by(models.Case.created_at)).all():
                case = repo.get(s.Case, row.id)
                snapshot, sections = ReadinessService(repo).refresh(case.id)
                applicable = [section for section in sections if section.applicable]
                drafts = [d.created_at for d in repo.list_for_case(s.DraftVersion, case.id)]
                events = sorted(repo.list_for_case(s.WorkflowEvent, case.id), key=lambda e: (e.created_at, e.id))
                returned = returned_scope(repo, case.id) if case.workflow_state == 'Returned to CA' else []
                result.append(dict(id=case.id, borrower_name=case.borrower_name, case_type=case.case_type, team_id=case.team_id,
                    synthetic_demo=case.id in demo_case_ids, workflow_state=case.workflow_state, waiting_for=WITH.get(case.workflow_state),
                    sections=len(applicable), drafted=sum(bool(section.current_draft_id) for section in applicable),
                    confirmed=sum(section.readiness == 'CA confirmed' for section in applicable),
                    update_required=sum(section.readiness == 'Stale' for section in applicable), returned_sections=returned,
                    inputs_outstanding=sum(e.applicable and e.status == 'Missing' for e in snapshot.expected),
                    suggested_checks=sum(check['open'] for check in sense.listing(repo, case.id) if check['current']),
                    last_event=dict(action=events[-1].action, actor=events[-1].actor, role=events[-1].role, at=events[-1].created_at.isoformat()) if events else None,
                    opened_at=(case.first_upload_at or case.created_at).isoformat(),
                    last_activity=max(drafts + [e.created_at for e in events] + [case.created_at]).isoformat()))
            session.commit()
            return result

    @router.get('/cases/{case_id}/dashboard')
    def dashboard(case_id: str):
        require_sessions()
        with sessions() as session:
            session.connection().exec_driver_sql('BEGIN IMMEDIATE')
            repo = Repository(session)
            case = case_for(repo, case_id)
            snapshot, sections = ReadinessService(repo).refresh(case_id)
            docs = repo.list_for_case(s.Document, case_id)
            current = {d.id for d in current_documents(docs, case)}
            expected = [e.model_dump(mode='json') | dict(name=snapshot.names[key(e)],
                satisfied=GapService(repo).satisfied(snapshot, e),
                details=snapshot.support[e.catalogue_id].details if e.catalogue_id else []) for e in snapshot.expected]
            names = {section.id: section.name for section in snapshot.config.template.sections}
            result = dict(case=case.model_dump(mode='json', exclude={'config_snapshot'}), synthetic_demo=case_id in demo_case_ids,
                documents=[d.model_dump(mode='json', exclude={'storage_path'}) | dict(current=d.id in current) for d in docs],
                expected_documents=expected,
                sections=[section.model_dump(mode='json') | dict(name=names[section.section_id]) for section in sections],
                gaps=snapshot.groups, generation_offers=generation_offers(snapshot),
                counts=dict(documents=dict(Counter(e['status'] for e in expected)),
                    draftable=sum(section.readiness in {'Can draft (partial)', 'Can draft (full)'} for section in sections),
                    open_mandatory=sum(e['mandatory'] and not e['satisfied'] for e in expected)),
                model_registry=dict(models=[m.public() for m in load_registry().models]),
                demo_spread_available=(case_id in demo_spread_available) if isinstance(demo_spread_available, (set, frozenset)) else bool(demo_spread_available and case_id in demo_case_ids),
                # Intake folders are per paper when several papers share the store.
                intake=dict(folders=(folders.get(case_id, []) if isinstance(folders, dict) else folders) or [], presets=intake_presets or []), search_mode=search_mode)
            session.commit()
            return result

    @router.get('/cases/{case_id}/documents/{document_id}/content')
    def content(case_id: str, document_id: str, preview: bool = False):
        require_sessions()
        if storage_root is None:
            raise HTTPException(503, 'Document content storage is not configured')
        with sessions() as session:
            repo = Repository(session)
            case_for(repo, case_id)
            try:
                doc = repo.get(s.Document, document_id)
            except ValueError:
                raise HTTPException(404, 'Document not found')
            if doc.case_id != case_id:
                raise HTTPException(404, 'Document not found')
            root, path = Path(storage_root).resolve(), Path(doc.storage_path)
            try:
                if (path.is_symlink() or not path.resolve().is_relative_to(root)
                        or not path.is_file() or path.stat().st_size > MAX_BYTES):
                    raise ValueError('Invalid content location')
                data = path.read_bytes()
                if sha256(data).hexdigest() != doc.content_hash:
                    raise ValueError('Changed content')
            except (OSError, ValueError):
                raise HTTPException(409, 'Stored content failed integrity validation')
            media, disposition = 'application/octet-stream', 'attachment'
            if preview:
                if Path(doc.original_filename).suffix.lower() != '.pdf' or not data.startswith(b'%PDF-'):
                    raise HTTPException(415, 'Inline preview is available for readable PDFs; download other formats')
                try:
                    with fitz.open(stream=data, filetype='pdf') as pdf:
                        if pdf.needs_pass or not pdf.page_count:
                            raise ValueError('Unreadable PDF')
                except Exception:
                    raise HTTPException(415, 'PDF cannot be previewed; download for manual review')
                media, disposition = 'application/pdf', 'inline'
            return Response(data, media_type=media, headers={
                'Content-Disposition': f"{disposition}; filename*=UTF-8''{quote(doc.original_filename, safe='')}",
                'X-Content-Type-Options': 'nosniff', 'Cache-Control': 'no-store'})

    return router
