from datetime import datetime, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from backend.app import schemas as s
from backend.app.repository import Repository
from backend.app.team_config import load_team

NOW = datetime(2026,11,10,tzinfo=timezone.utc)


def make_case(**changes):
    config = load_team('fig')
    return s.Case(**(dict(borrower_name='SYNTHETIC DEMO DATA — Test REIT',team_id='fig',config_version=config.template.version,config_hash=config.content_hash,case_type='renewal',borrower_type='reit',existing_client=True,new_to_bank=False) | changes))


def seed(repository):
    case = repository.save(make_case())
    owned = dict(case_id=case.id)
    template = repository.save(s.TemplateVersion(team_id='fig',display_version='test-only',content_hash='a'*64,storage_path='runtime/test.docx'))
    document = repository.save(s.Document(**owned,catalogue_id=4,entity=case.borrower_name,content_hash='b'*64,storage_path='runtime/report.pdf',origin='public',synthetic=False,original_filename='public.pdf',url='https://example.org/report.pdf',retrieved_at=NOW))
    evidence = repository.save(s.Evidence(**owned,document_id=document.id,page=1,excerpt='Public example',origin='public',synthetic=False,url=document.url,retrieved_at=NOW))
    draft = repository.save(s.DraftVersion(**owned,section_id=1,text='SYNTHETIC DEMO DATA — fixture draft',config_hash=case.config_hash,prompt_version='1',model_version='mock-v1',template_version_id=template.id,input_fingerprint='inputs-1',author='test-ca',document_ids=[document.id]))
    es = repository.save(s.ESVersion(**owned,section_versions={1:draft.id},config_hash=case.config_hash,template_version_id=template.id,author='test-ca',purpose='working'))
    return case,template,document,evidence,draft,es


def test_all_entities_round_trip_with_relationships(database):
    repo = Repository(database)
    case,template,document,evidence,draft,es = seed(repo)
    owned=dict(case_id=case.id)
    case.active_es_version_id=es.id
    repo.save(case)
    expected = repo.save(s.ExpectedDocument(**owned,catalogue_id=4,applicable=True,mandatory=True,reason='Annual report or financial statements',alternative_group='financial_report',usual_owner='client',section_ids=[3,4,5,6,10],status='Found publicly',document_ids=[document.id]))
    section=repo.save(s.Section(**owned,section_id=1,readiness='Drafted',completeness='partial',gaps=['CAS not provided'],current_draft_id=draft.id))
    activation=repo.save(s.TemplateActivation(team_id='fig',template_version_id=template.id,actor='admin',role='template admin'))
    change=repo.save(s.TemplateChange(template_version_id=template.id,section_id=1,anchor='heading',before='A',after='B',category='prompt',reason='Changed instruction'))
    chat=repo.save(s.ChatMessage(**owned,section_id=1,base_draft_id=draft.id,actor='test-ca',text='SYNTHETIC DEMO DATA — test input'))
    ca=repo.save(s.CAInput(**owned,message_id=chat.id,actor='test-ca',fact='SYNTHETIC DEMO DATA — 2.30',numeric_input={'value':'2.30'}))
    ca_evidence=repo.save(s.Evidence(**owned,ca_input_id=ca.id,excerpt=ca.fact,origin='CA input',synthetic=True))
    spread=repo.save(s.Spread(**owned,document_ids=[document.id],ca_input_ids=[ca.id],version='1',values={'amount':'2.30'},validation_status='valid'))
    computed=repo.save(s.ComputedValue(**owned,spread_id=spread.id,metric='test_amount',formula_version='1',operands={'amount':Decimal('2.300000000000000001')},operand_evidence_ids={'amount':[ca_evidence.id]},unit='currency',currency='SGD',period='FY2025',scope='test',value=Decimal('2.300000000000000001'),validated=True,synthetic=True))
    citation=repo.save(s.Citation(**owned,evidence_id=evidence.id,draft_id=draft.id,claim_or_cell='claim-1'))
    cell=repo.save(s.Citation(**owned,evidence_id=ca_evidence.id,computed_value_id=computed.id,claim_or_cell='operand:amount'))
    proposal=repo.save(s.SectionProposal(**owned,message_id=chat.id,section_id=1,base_draft_id=draft.id,proposed_text='SYNTHETIC DEMO DATA — proposed wording',evidence_ids=[ca_evidence.id],computed_value_ids=[computed.id],model_version='mock-v1'))
    event=repo.save(s.WorkflowEvent(**owned,action='submit',actor='test-ca',role='CA',from_state='Draft',to_state='Submitted to Credit Head',es_version_id=es.id))
    comment=repo.save(s.Comment(**owned,section_id=1,draft_id=draft.id,es_version_id=es.id,author='head',role='Credit Head',body='Test comment'))
    check=repo.save(s.SubmissionCheck(**owned,es_version_id=es.id,section_results={1:{'confirmed':False}},mandatory_gap_reasons={},freshness_results={1:True},passed=False,checked_by='test-ca'))
    question=repo.save(s.ApproverQuestion(**owned,es_version_id=es.id,section_ids=[1],question='Test question?',asked_by='approver'))
    all_records=[case,template,document,evidence,draft,es,expected,section,activation,change,chat,ca,ca_evidence,spread,computed,citation,cell,proposal,event,comment,check,question]
    database.commit()
    database.expunge_all()
    for record in all_records:
        assert repo.get(type(record),record.id) == record
    assert repo.list_for_case(s.Section,case.id)[0].gaps == ['CAS not provided']
    assert repo.get(s.ComputedValue,computed.id).value == Decimal('2.300000000000000001')
    assert repo.get(s.Document,document.id).retrieved_at.tzinfo is not None
    assert len({type(r).__name__ for r in all_records}) == 20


def test_cross_case_section_and_missing_references(database):
    repo=Repository(database)
    case,template,document,evidence,draft,es=seed(repo)
    other=repo.save(make_case())
    with pytest.raises(ValueError,match='Cross-case'):
        repo.save(s.Section(case_id=other.id,section_id=1,current_draft_id=draft.id))
    with pytest.raises(ValueError,match='Cross-section'):
        repo.save(s.Section(case_id=case.id,section_id=2,current_draft_id=draft.id))
    with pytest.raises(ValueError,match='Missing'):
        repo.save(s.Section(case_id=case.id,section_id=1,current_draft_id='missing'))
    with pytest.raises(ValueError,match='Unknown configured section'):
        repo.save(s.Section(case_id=case.id,section_id=99))
    with pytest.raises(ValueError,match='Cross-case'):
        repo.save(s.ExpectedDocument(case_id=other.id,catalogue_id=4,applicable=True,mandatory=True,reason='test',usual_owner='client',section_ids=[4],status='Provided',document_ids=[document.id]))
    with pytest.raises(ValueError,match='Snapshot section'):
        repo.save(s.ESVersion(case_id=case.id,section_versions={2:draft.id},config_hash=case.config_hash,template_version_id=template.id,author='ca',purpose='working'))


def test_immutable_versions_and_database_constraints(database):
    repo=Repository(database)
    case,template,document,evidence,draft,es=seed(repo)
    database.commit()
    with pytest.raises(ValueError,match='append-only'):
        repo.save(draft.model_copy(update={'text':'changed'}))
    with pytest.raises(ValueError,match='immutable'):
        repo.save(document.model_copy(update={'content_hash':'c'*64}))
    document=document.model_copy(update={'confirmed_by':'test-ca','confirmed_at':NOW})
    repo.save(document)
    database.commit()
    for command in ('UPDATE draft_version SET text = :value WHERE id = :id','DELETE FROM draft_version WHERE id = :id'):
        with pytest.raises(IntegrityError,match='immutable'):
            database.execute(text(command),dict(value='changed',id=draft.id))
        database.rollback()
    with pytest.raises(IntegrityError):
        database.execute(text('UPDATE document SET case_id = :case WHERE id = :id'),dict(case='missing',id=document.id))
    database.rollback()
    section=repo.save(s.Section(case_id=case.id,section_id=1))
    database.commit()
    with pytest.raises(IntegrityError,match='FOREIGN KEY'):
        database.execute(text('UPDATE section SET case_id = :case WHERE id = :id'),dict(case='missing',id=section.id))
    database.rollback()
    with pytest.raises(IntegrityError):
        repo.save(s.Section(case_id=case.id,section_id=1))
    database.rollback()


@pytest.mark.parametrize('make',[
    lambda: make_case(existing_client=False),
    lambda: make_case(existing_client=False,new_to_bank=True),
    lambda: s.Section(case_id='c',section_id=1,applicable=False),
    lambda: s.Section(case_id='c',section_id=1,readiness='CA confirmed'),
    lambda: s.ExpectedDocument(case_id='c',catalogue_id=4,applicable=True,mandatory=True,reason='test',usual_owner='client',section_ids=[4],status='Dismissed'),
    lambda: s.Evidence(case_id='c',document_id='d',excerpt='text',origin='upload',synthetic=True),
    lambda: s.Evidence(case_id='c',ca_input_id='i',excerpt='text',origin='upload',synthetic=True),
    lambda: s.ApproverQuestion(case_id='c',es_version_id='es',section_ids=[1],question='?',asked_by='a',resubmitted_es_version_id='es2'),
    lambda: s.TemplateChange(template_version_id='t',anchor='a',before='b',after='c',category='automatic',reason='test'),
    lambda: s.Citation(case_id='c',evidence_id='e',claim_or_cell='claim'),
    lambda: s.TemplateVersion(team_id='fig',display_version='1',content_hash='invalid',storage_path='p'),
    lambda: s.ChatMessage(case_id='c',section_id=1,base_draft_id='d',actor='ca',text='x',created_at=datetime(2026,11,10)),
])
def test_invalid_entities(make):
    with pytest.raises(ValidationError):
        make()


def test_public_and_synthetic_provenance(database):
    repo=Repository(database)
    case,template,document,evidence,draft,es=seed(repo)
    with pytest.raises(ValueError,match='provenance'):
        repo.save(s.Evidence(case_id=case.id,document_id=document.id,page=1,excerpt='text',origin='upload',synthetic=True))
    with pytest.raises(ValidationError):
        s.Document(case_id=case.id,catalogue_id=4,entity='test',content_hash='b'*64,storage_path='p',origin='public',synthetic=False,original_filename='p')
    with pytest.raises(ValidationError,match='Each operand'):
        s.ComputedValue(case_id=case.id,metric='x',formula_version='1',operands={'a':Decimal('1')},operand_evidence_ids={},unit='x',period='2025',scope='test',value=Decimal('1'),synthetic=False)


def test_pinned_configuration_survives_yaml_change(database):
    from backend.app.team_config import TeamConfig
    repo=Repository(database)
    case,template,document,evidence,draft,es=seed(repo)
    changed=load_team('fig').model_dump()
    changed['template']['version']='future-version'
    changed=TeamConfig.model_validate(changed)
    future_repo=Repository(database,config_loader=lambda team: changed)
    future_repo.save(s.Section(case_id=case.id,section_id=1))
    assert future_repo.get(s.Case,case.id).config_snapshot['template']['version']==case.config_version
    with pytest.raises(ValueError,match='configuration'):
        future_repo.save(s.ESVersion(case_id=case.id,section_versions={1:draft.id},config_hash='wrong',template_version_id=template.id,author='ca',purpose='working'))
    with pytest.raises(ValueError,match='workflow event'):
        repo.save(s.WorkflowEvent(case_id=case.id,action='approve',actor='admin',role='template admin',from_state='Draft',to_state='Approved',es_version_id=es.id))
