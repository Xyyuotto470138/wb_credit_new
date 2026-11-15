"""B01 application factory. Import and health checks perform no external I/O."""
from fastapi import FastAPI

from .llm import Provider, create_provider
from .team_config import load_team
from .api.workflow import workflow_router
from .api.review import review_router
from .api.documents import documents_router
from .api.readiness import readiness_router
from .api.gaps import gaps_router
from .api.dashboard import dashboard_router
from .api.evidence import evidence_router
from .api.templates import templates_router
from .api.spreads import spreads_router
from .api.analytics import analytics_router
from .api.drafts import drafts_router
from .api.sections import sections_router
from .api.exports import exports_router
from .api.chat import chat_router
from .api.model_registry import models_router
from .es2.api import es2_router
from .api.submission_checks import submission_checks_router
from .api.auth import auth_router


def create_app(team_id='fig', provider: Provider | None = None, *, sessions=None, storage_root=None, intake_folders=None, search_provider=None, dashboard_folders=None, intake_presets=None, demo_case_ids=(), template_storage_root=None, drafting_provider=None, export_storage_root=None, chat_provider=None, demo_spread_available=False):
    config = load_team(team_id)
    app = FastAPI(title='WB Credit')
    app.state.team_config = config
    app.state.provider = provider if provider is not None else create_provider()
    app.include_router(auth_router())
    app.include_router(workflow_router(sessions, storage_root, template_storage_root))
    app.include_router(review_router(sessions))
    app.include_router(documents_router(sessions, storage_root, intake_folders))
    app.include_router(readiness_router(sessions))
    app.include_router(gaps_router(sessions, storage_root, search_provider))
    app.include_router(evidence_router(sessions, storage_root))
    app.include_router(spreads_router(sessions, storage_root, app.state.provider))
    app.include_router(analytics_router(sessions, storage_root))
    app.include_router(submission_checks_router(sessions, storage_root, template_storage_root))
    app.include_router(models_router(sessions, storage_root, template_storage_root))
    app.state.es2 = es2_router(sessions, storage_root)
    app.include_router(app.state.es2)
    app.include_router(chat_router(sessions, storage_root, template_storage_root, chat_provider))
    app.include_router(sections_router(sessions, storage_root, template_storage_root, drafting_provider))
    app.include_router(drafts_router(sessions, storage_root, template_storage_root, drafting_provider))
    app.include_router(exports_router(sessions, storage_root, template_storage_root, export_storage_root))
    app.include_router(templates_router(sessions, template_storage_root))
    app.include_router(dashboard_router(sessions, storage_root, folders=dashboard_folders,
        intake_presets=intake_presets, search_mode=search_provider.name if search_provider else 'off', demo_case_ids=demo_case_ids, demo_spread_available=demo_spread_available))

    @app.get('/health')
    def health():
        return {'status': 'ok', 'team': config.template.team_id, 'config_hash': config.content_hash, 'provider': app.state.provider.get_provider_info()}

    return app
