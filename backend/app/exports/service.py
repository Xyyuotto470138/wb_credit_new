"""Immutable draft export snapshots. No submission, approval or source refresh."""
from hashlib import sha256
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .. import schemas as s
from ..repository import Repository
from ..retrieval import EvidenceService
from ..retrieval.service import identity, ContentIntegrityError
from ..services.gaps import request_list
from ..services.locks import WorkflowConflict, require_working
from ..services.readiness import ReadinessService
from ..services.templates import TemplateRegistry, TemplateIntegrityError
from .word import TemplateCopy
from .mapping import Mapper, VERSION
from ..es2.spec import load_spec


class ExportConflict(ValueError):
    pass


class ExportRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    actor: str = Field(min_length=1,max_length=200,pattern=r'.*\S.*')
    role: Literal['CA'] = 'CA'
    expected_preview_token: str = Field(min_length=1)


class ExportService:
    def __init__(self, repo: Repository, storage_root, template_storage_root, export_storage_root=None):
        self.repo=repo
        self.evidence=EvidenceService(repo,storage_root)
        self.templates=TemplateRegistry(repo,template_storage_root)
        self.root=Path(export_storage_root or Path(storage_root).parent/'exports').resolve()

    def prepare(self, case_id):
        case=self.repo.get(s.Case,case_id)
        try:
            require_working(self.repo, case_id)
        except WorkflowConflict as error:
            raise ExportConflict('New draft exports require Draft state or a recorded return; use the saved workflow snapshot while locked') from error
        gaps,states=ReadinessService(self.repo).refresh(case_id)
        drafts={st.section_id:self.repo.get(s.DraftVersion,st.current_draft_id).model_dump(mode='json')
                for st in states if st.current_draft_id and st.applicable}
        pins={d['template_version_id'] for d in drafts.values()}
        if len(pins)>1:
            raise ExportConflict('Section template pins differ; choose a consistent working version before export')
        template=self.templates.get(case.team_id,next(iter(pins))) if pins else self.templates.active(case.team_id)
        if not template:
            raise ExportConflict('No active/pinned template available')
        content=self.templates.content(case.team_id,template.id)
        report=template.parsed_map
        sources={}
        for sid,draft in drafts.items():
            if draft['case_id']!=case.id or draft['section_id']!=sid or draft['config_hash']!=case.config_hash:
                raise ExportConflict('Draft ownership/section/configuration mismatch')
            spans=draft['claim_spans']
            if not spans or spans[0].get('kind')!='draft_metadata':
                raise ExportConflict(f'Section {sid}: structured claims required; redraft legacy text')
            for claim in spans[1:]:
                start,end=claim.get('start'),claim.get('end')
                if not isinstance(start,int) or not isinstance(end,int) or not 0<=start<end<=len(draft['text']) or claim['text'] not in draft['text'][start:end]:
                    raise ExportConflict(f'Section {sid}: claim/text mismatch')
                refs=claim.get('evidence_ids',[])
                if not refs and claim['kind'] not in {'case_input','ca_position'} and not claim.get('section_refs') and not claim.get('computed_ref'):
                    raise ExportConflict(f'Section {sid}: unsupported uncited claim')
                for ref in refs:
                    resolved=self.evidence.resolve(case_id,ref)
                    saved=spans[0]['source_register'].get(ref)
                    if not saved or any(saved[k]!=resolved[k] for k in ('content_hash','document_id','page','synthetic','url','retrieved_at')):
                        raise ExportConflict('Saved source provenance does not match immutable evidence')
                    # Preserve draft-time public confirmation labels; record currentness separately.
                    sources[ref]=saved | {'current_at_export':resolved['current']}
                ids=claim.get('computed_value_ids',[])+([claim['computed_value_id']] if claim.get('computed_value_id') else [])
                for value_id in ids:
                    value=self.repo.get(s.ComputedValue,value_id)
                    operands={r for group in value.operand_evidence_ids.values() for r in group}
                    if value.case_id!=case_id or not value.validated or value.gaps or value.value is None or not operands or not operands<=set(refs):
                        raise ExportConflict('Invalid computed claim or operand citations')
                    if claim.get('computed_value_id')==value_id and claim.get('value')!=value.model_dump(mode='json'):
                        raise ExportConflict('Computed claim differs from immutable value')
                    if claim.get('reviewed_value', {}).get('id') == value_id and claim['reviewed_value'] != value.model_dump(mode='json'):
                        raise ExportConflict('Reviewed financial claim differs from immutable value')
            if spans[0].get('parts') is not None:
                # Specification-driven drafts also cite sources from table cells and answers; keep them in the source list.
                for ref,saved in spans[0].get('source_register',{}).items():
                    sources.setdefault(ref,saved | {'current_at_export':self.evidence.resolve(case_id,ref)['current']})
            for table in spans[0].get('computed_tables',[]):
                run=self.repo.get(s.Spread,spans[0]['computation_id'])
                if run.case_id!=case_id or table not in run.values.get('tables',[]):
                    raise ExportConflict('Draft table differs from immutable Python computation')
        sections={str(st.section_id):dict(section_id=st.section_id,applicable=st.applicable,
            na_reason=st.na_reason,readiness=st.readiness,completeness=st.completeness,
            input_fingerprint=st.input_fingerprint,editor_revision=st.editor_revision,
            gaps=st.gaps,draft=drafts.get(st.section_id)) for st in states}
        mapping_gaps=[dict(anchor='template',reason=g) for g in template.parse_gaps]
        canonical={st.section_id for st in states}
        mapped={r['section_id'] for r in report['sections'] if r['mapped']}
        blockers=[]
        if mapped!=canonical:
            blockers.append('Canonical section headings are missing/ambiguous; cannot retain all sections in a Word export')
        # A missing/ambiguous content anchor is reviewable, but its unbound sample
        # cells cannot safely remain in a deliverable. Preview/metadata name it.
        if template.parse_gaps:
            blockers.append('Template mapping gaps require resolution before Word export; no positional fallback')
        manifest=dict(format_version=VERSION,status='DRAFT — CA REVIEW REQUIRED',case_id=case_id,
            borrower_name=case.borrower_name,config_hash=case.config_hash,workflow_state=case.workflow_state,
            template=dict(id=template.id,display_version=template.display_version,content_hash=template.content_hash,
                          parser_version=report['parser_version'],mapping_hash=report['mapping_hash']),
            sections=sections,sources=dict(sorted(sources.items())),mapping_gaps=mapping_gaps,
            request_groups=gaps.groups,request_list=request_list(gaps),blockers=blockers,
            public_source_policy='Numbered markers resolve to the Sources appendix with document/page, labels and public URL/retrieval dates; exact saved drafts and evidence remain in this companion manifest.',
            layout_review='Template layout retained; export-specific pagination needs visual review. Not a final or approved ES.')
        docx=None
        if not blockers:
            spec=load_spec(case.team_id)
            if spec:
                # Model suggestions the analyst has not yet looked at are listed with the open items.
                from ..es2 import sense
                manifest['suggested_checks']=[f"Section {check['section_id']}: suggested check, {f['table_title']}"
                    + (f", {f['row_label']}" if f['row_label'] else '') + (f", {f['column']}" if f['column'] else '') + f": {f['reason']} (Model suggestion for a human check.)"
                    for check in sorted(sense.listing(self.repo, case_id), key=lambda c: c['section_id']) if check['current']
                    for f in check['findings'] if f['id'] not in check['resolutions']]
                # Teams with an ES specification are filled part by part from their structured drafts.
                from ..es2.export import fill
                docx=fill(TemplateCopy(content,report),manifest,case,spec,self.evidence.storage_root)
            else:
                docx=Mapper(TemplateCopy(content,report),manifest).run()
        manifest['preview_token']=identity(manifest)
        return manifest,docx

    def create(self, case_id, request):
        manifest,content=self.prepare(case_id)
        if request.expected_preview_token!=manifest['preview_token']:
            raise ExportConflict('Export inputs/versions changed; reload the preview before exporting')
        if manifest['blockers']:
            raise ExportConflict('; '.join(manifest['blockers']))
        es=self.repo.save(s.ESVersion(case_id=case_id,section_versions={int(sid):sec['draft']['id'] for sid,sec in manifest['sections'].items() if sec['draft']},
            config_hash=manifest['config_hash'],template_version_id=manifest['template']['id'],author=request.actor,purpose='export'))
        manifest.update(es_version_id=es.id,created_at=es.created_at.isoformat(),author=request.actor)
        artifact=s.ExportArtifact(case_id=case_id,es_version_id=es.id,content_hash=sha256(content).hexdigest(),manifest=manifest)
        self.root.mkdir(parents=True,exist_ok=True)
        path=self.root/(artifact.content_hash+'.docx')
        if path.is_symlink() or path.resolve().parent!=self.root:
            raise TemplateIntegrityError('Export storage boundary mismatch')
        if path.exists():
            if path.read_bytes()!=content:
                raise TemplateIntegrityError('Export bytes corrupted')
        else:
            with path.open('xb') as stream: stream.write(content)
        return self.repo.save(artifact)

    def get(self,case_id,artifact_id):
        artifact=self.repo.get(s.ExportArtifact,artifact_id)
        if artifact.case_id!=case_id:
            raise ValueError('Export not found for case')
        return artifact

    def content(self,case_id,artifact_id):
        artifact=self.get(case_id,artifact_id)
        path=self.root/(artifact.content_hash+'.docx')
        if path.is_symlink() or path.resolve().parent!=self.root:
            raise ContentIntegrityError('Export storage boundary mismatch')
        try: content=path.read_bytes()
        except OSError as error: raise ContentIntegrityError('Export bytes unavailable') from error
        if sha256(content).hexdigest()!=artifact.content_hash:
            raise ContentIntegrityError('Export hash mismatch')
        return content
