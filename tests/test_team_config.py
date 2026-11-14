from pathlib import Path
import re
import shutil

import pytest
import yaml
from pydantic import ValidationError

from backend.app.schemas import Case
from backend.app.team_config import CONFIG_ROOT, TeamConfig, load_team


def case(**changes):
    config = load_team('fig')
    data = dict(borrower_name='SYNTHETIC DEMO DATA — Example REIT', team_id='fig', config_version=config.template.version, config_hash=config.content_hash, case_type='new', borrower_type='reit', existing_client=False, new_to_bank=True)
    return Case(**(data | changes))


def test_exact_project_catalogue_and_sections():
    config = load_team('fig')
    project = (Path(__file__).resolve().parents[1] / 'WB_Credit_PROJECT.md').read_text()
    rows = project.split('### 3.1 Sections')[1].split('**Section dependencies')[0]
    expected = [[v.strip() for v in row.strip('|').split('|')] for row in rows.splitlines() if re.match(r'\| \d+ \|', row)]
    assert len(config.template.sections) == len(expected) == 14
    for actual, (n, desc, inputs, rule, mode) in zip(config.template.sections, expected):
        assert (actual.id, actual.description, actual.main_inputs, actual.case_rule, actual.draft_mode) == (int(n), desc, inputs, rule, mode)
    rows = project.split('### 3.2 Input document catalogue')[1].split('"Conditional"')[0]
    expected = [[v.strip() for v in row.strip('|').split('|')] for row in rows.splitlines() if re.match(r'\| \d+ \|', row)]
    assert len(config.catalogue.items) == len(expected) == 22
    for actual, (n,name,source,public,applies,sections,mandatory) in zip(config.catalogue.items, expected):
        assert (actual.id, actual.name, actual.usual_source, actual.public_availability, actual.applies_when, actual.sections, actual.mandatory_label) == (int(n),name,source,public,applies,[int(v.strip()) for v in sections.split(',')],mandatory)


def test_case_rule_matrix():
    config = load_team('fig')
    def required(c):
        return {i.id for i in config.catalogue.items if i.applicable_when.matches(c) and i.mandatory_when.matches(c)}
    assert required(case()) == {1,2,4,6,7,10,19,20}
    assert required(case(case_type='renewal',existing_client=True,new_to_bank=False)) == {1,2,3,4,6,7,10,17,19,20,22}
    full = case(case_type='renewal',existing_client=True,new_to_bank=False,borrower_type='fund',financial_covenants=True,covenants=True,property_or_asset_security=True,insured_security_or_assets=True,new_money=True,property_income_repayment=True,bureau_covered=True)
    assert required(full) == set(range(1,23)) - {11,12,18}
    assert 14 in required(case(facility_types=['term']))
    assert 14 in required(case(facility_types=['acquisition']))
    assert 5 in required(case(has_information_memorandum=True))
    assert {i.id for i in config.catalogue.items if i.public_search} == {4,5,6,20}
    assert config.catalogue.items[9].public_support == 'external only'
    assert config.catalogue.items[8].public_support == 'partial only'
    assert config.rules.alternatives[0].members == [4,6]
    assert not config.template.sections[2].mandatory_when.matches(case())
    assert config.template.sections[2].mandatory_when.matches(full)
    assert not config.template.sections[12].applicable_when.matches(case())
    assert config.template.sections[12].applicable_when.matches(full)


@pytest.mark.parametrize('mutation', [
    lambda d: d['catalogue']['items'][0]['sections'].append(99),
    lambda d: d['catalogue']['items'][0]['applicable_when'].update(op='eval'),
    lambda d: d['catalogue']['items'][0]['applicable_when'].update(op='eq',field='secret_key',value=True),
    lambda d: d['catalogue']['items'][0]['applicable_when'].update(op='eq',field='existing_client',value='yes'),
    lambda d: d['dependencies']['items'][6]['requires'].append(9),
    lambda d: d['dependencies']['items'][0]['requires'].append(99),
    lambda d: d['analytics']['sets']['reit']['metrics'][0]['formula'].update(op='python'),
    lambda d: d['analytics']['sets']['reit']['metrics'][0]['formula'].update(operands=[]),
    lambda d: d['workflow']['transitions'][5].update(action='auto_approve'),
    lambda d: d['workflow']['transitions'][5].update(role='template admin'),
    lambda d: d['workflow']['transitions'][5].update(from_states=['Declined']),
    lambda d: d['workflow']['transitions'][5].update(from_states=['Draft']),
    lambda d: d['workflow']['transitions'][6].update(requirements=[]),
    lambda d: d['workflow']['transitions'][5].update(to_state='Declined'),
    lambda d: d['rules']['alternatives'][0].update(members=[4,999]),
    lambda d: d['prompts']['items'].pop(),
])
def test_invalid_config_rejected(mutation):
    data = load_team('fig').model_dump()
    mutation(data)
    with pytest.raises(ValidationError):
        TeamConfig.model_validate(data)


def test_alternate_team_and_conditions_toggle(tmp_path):
    folder = tmp_path / 'test-team'
    shutil.copytree(CONFIG_ROOT / 'fig', folder)
    path = folder / 'template.yaml'
    data = yaml.safe_load(path.read_text())
    data['team_id'] = 'test-team'
    data['version'] = 'test-only-1'
    data['sections'][0]['name'] = 'Test-only purpose'
    path.write_text(yaml.safe_dump(data))
    path = folder / 'workflow.yaml'
    data = yaml.safe_load(path.read_text())
    next(t for t in data['transitions'] if t['action']=='approve_with_conditions')['enabled'] = False
    path.write_text(yaml.safe_dump(data))
    config = load_team('test-team', tmp_path)
    assert config.template.team_id == 'test-team'
    assert config.content_hash != load_team('fig').content_hash
    assert not next(t for t in config.workflow.transitions if t.action=='approve_with_conditions').enabled
    with pytest.raises(ValueError):
        load_team('../fig', tmp_path)


def test_analytics_and_ca_owned_modes():
    config = load_team('fig')
    metrics = config.analytics.sets['reit'].metrics
    assert len(metrics) >= 21  # Ten core measures plus mapped template rows/sensitivity.
    assert [t.value for t in metrics[0].thresholds] == ['50']
    assert [t.value for t in metrics[1].thresholds] == ['1.5','1.8']
    assert all(t.verification == 'MAS source checked 2026-11-10' for m in metrics for t in m.thresholds)
    assert config.template.sections[13].requires_ca_position
    assert config.template.sections[11].requires_supplied_internal_rating
    assert config.template.sections[7].unsecured_requires_ca_confirmation
    assert config.dependencies.items[8].requires == [7,10]
    assert config.dependencies.items[10].requires == list(range(3,11))
    assert config.dependencies.items[13].mandatory_only
    assert load_team('fig').content_hash == config.content_hash
