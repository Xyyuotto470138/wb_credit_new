"""Explicit local Gate 2 startup; imports alone do not create runtime files."""
from contextlib import asynccontextmanager
from pathlib import Path

import yaml

from . import schemas as s
from .database import create_database
from .main import create_app
from .repository import Repository
from .services.search import SavedPublicPackProvider
from .services.templates import TemplateRegistry
from .team_config import load_team

ROOT = Path(__file__).resolve().parents[2]


DEFAULT_PACK = ROOT / 'demo/synthetic'


def demo_settings(pack=None):
    pack = (ROOT / pack).resolve() if pack else DEFAULT_PACK  # a relative pack path is read from the project root
    case = yaml.safe_load((pack / 'case.yaml').read_text())
    manifest = yaml.safe_load((pack / 'manifest.yaml').read_text())
    presets = []
    for entry in manifest['documents']:
        metadata = dict(entity=entry['entity'], period=entry.get('period_end', entry['date']), synthetic=True)
        for field in ('catalogue_id', 'suggestion_id'):
            if entry.get(field) is not None:
                metadata[field] = entry[field]
        presets.append(dict(filename=Path(entry['file']).name, sha256=entry['sha256'],
                            metadata=metadata, tranche=entry.get('tranche')))
    if pack == DEFAULT_PACK:
        folders = {f'tranche_{i}': pack / f'tranche_{i}' for i in (1, 2, 3)}
        labels = {folder_id: f'Tranche {i} · synthetic demo files' for i, folder_id in enumerate(folders, start=1)}
    else:  # other packs: one scan folder per top-level directory named in the manifest
        names = list(dict.fromkeys(Path(entry['file']).parts[0] for entry in manifest['documents']))
        folders = {name: pack / name for name in names}
        labels = {name: f"{name.replace('_', ' ').capitalize()} · synthetic demo files" for name in names}
    options = [dict(id=folder_id, label=labels[folder_id],
        metadata_by_path={p['filename']: p['metadata'] for p in presets if p['tranche'] == i})
        for i, folder_id in enumerate(folders, start=1)]
    return case, folders, options, presets


def seed_case(sessions, pack=None):
    fixture, _, _, _ = demo_settings(pack)
    config = load_team(fixture['app_case']['team_id'])
    with sessions.begin() as session:
        repo = Repository(session)
        try:
            return repo.get(s.Case, fixture['case_id'])
        except ValueError:
            return repo.save(s.Case(id=fixture['case_id'], borrower_name=fixture['borrower']['name'],
                public_identifiers={k: fixture['borrower'][k] for k in ('sgx_code', 'isin') if k in fixture['borrower']},
                config_version=config.template.version, config_hash=config.content_hash, **fixture['app_case']))


def create_local_app():
    return create_demo_app(ROOT / 'runtime/gate1')


class CaseSearch:
    """One saved public pack per paper: the first pack whose borrower matches answers the search."""
    name = 'saved-pack'

    def __init__(self, providers):
        self.providers = providers

    def search(self, public_identity):
        result = None
        for provider in self.providers:
            result = provider.search(public_identity)
            if result.outcome != 'no match':
                break
        return result


def create_demo_app(runtime, pack=None, more=()):
    """Local demo on one synthetic pack. The default pack is the offline ESR-REIT renewal case.

    `more` names further packs, each seeded as its own paper in the same store, so the papers list can
    switch between them. The first pack's paper stays first in every listing."""
    runtime = Path(runtime)
    runtime.mkdir(parents=True, exist_ok=True)
    engine, sessions = create_database(runtime / 'wb_credit.sqlite')
    is_default = lambda name: name is None or (ROOT / name).resolve() == DEFAULT_PACK
    packs = [pack] + [name for name in more if (ROOT / name).resolve() != ((ROOT / pack).resolve() if pack else DEFAULT_PACK)]
    folders, options, presets, providers, case_ids, spread_cases = {}, {}, [], [], [], set()
    for name in packs:
        case = seed_case(sessions, name)
        fixture, pack_folders, pack_options, pack_presets = demo_settings(name)
        with sessions() as session:
            session.connection().exec_driver_sql('BEGIN IMMEDIATE')
            TemplateRegistry(Repository(session), runtime / 'templates').seed_owner_templates(case.team_id, ROOT)
            session.commit()
        folders.update(pack_folders)
        options[case.id] = pack_options
        presets += pack_presets
        providers.append(SavedPublicPackProvider() if is_default(name) else SavedPublicPackProvider((ROOT / fixture['borrower']['public_manifest']).parent))
        case_ids.append(case.id)
        if is_default(name):
            spread_cases.add(case.id)
    app = create_app(sessions=sessions, storage_root=runtime / 'blobs', intake_folders=folders,
        search_provider=providers[0] if len(providers) == 1 else CaseSearch(providers), dashboard_folders=options, intake_presets=presets,
        demo_case_ids=tuple(case_ids), template_storage_root=runtime / 'templates', demo_spread_available=spread_cases)
    for case_id in spread_cases:
        from .api.demo import demo_router
        app.include_router(demo_router(sessions, runtime / 'blobs', case_id))

    @asynccontextmanager
    async def lifespan(app):
        try:
            yield
        finally:
            engine.dispose()

    app.router.lifespan_context = lifespan
    return app
