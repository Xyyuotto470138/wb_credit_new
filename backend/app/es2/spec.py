"""Load a team's ES specification (config/teams/<team>/es_spec.yaml). Teams without one use the first-generation path."""
from functools import lru_cache
from pathlib import Path

import yaml

CONFIG_ROOT = Path(__file__).resolve().parents[3] / 'config/teams'


@lru_cache(maxsize=None)
def _load(path, modified):
    return yaml.safe_load(Path(path).read_text())


def load_spec(team_id):
    path = CONFIG_ROOT / team_id / 'es_spec.yaml'
    return _load(str(path), path.stat().st_mtime) if path.exists() else None


def section_parts(spec, section_id):
    return next(s for s in spec['sections'] if s['id'] == section_id)['parts']


def column_names(part):
    return [c['name'] if isinstance(c, dict) else c for c in part.get('columns', [])]


def column_spec(part, name):
    return next((c for c in part.get('columns', []) if isinstance(c, dict) and c['name'] == name), {})


def applies(part, case):
    """Parts marked only_when: existing_client do not apply to a new-to-bank borrower."""
    return part.get('only_when') != 'existing_client' or bool(case.existing_client)


LENDING_TYPES = Path(__file__).resolve().parents[3] / 'config/lending_types.yaml'


def lending_types():
    """The lending types a paper can be started with: id, label and the focus given to the drafting model."""
    return _load(str(LENDING_TYPES), LENDING_TYPES.stat().st_mtime)['types'] if LENDING_TYPES.exists() else []


def lending_type(type_id):
    return next((t for t in lending_types() if t['id'] == type_id), None)


def lending_note(case):
    """The paragraph added to a drafting request for a paper that has a lending type; empty for one that has none."""
    found = lending_type(getattr(case, 'lending_type', None))
    if not found:
        return ''
    return (f"\n\nLending type: {found['label']}\n{' '.join(found['focus'].split())}\n"
            'Give these points more weight where the parts asked for and the evidence cover them. This sets emphasis only: '
            'draft only the parts asked for and cite every statement. Not every point will be covered by the documents. '
            'Where one is not, leave it out or name it under "gaps"; do not fill it from general knowledge.')
