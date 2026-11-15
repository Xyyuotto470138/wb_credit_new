"""Session pattern adapted from Phase 1 backend/app/database.py, 2026-11-10.
No engine, directory creation, environment/key loading or connection at import.
"""
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker


class Base(DeclarativeBase):
    pass


def create_database(path: Path | str):
    engine = create_engine('sqlite:///:memory:' if str(path) == ':memory:' else f'sqlite:///{Path(path).resolve()}', connect_args={'check_same_thread': False})

    @event.listens_for(engine, 'connect')
    def foreign_keys(connection, _):
        connection.execute('PRAGMA foreign_keys=ON')

    from . import models  # noqa: F401
    Base.metadata.create_all(engine)
    # SQLite protects historical snapshots even when a caller bypasses the repository.
    from .repository import IMMUTABLE
    with engine.begin() as connection:
        # Additive B04 upgrade for databases initialized by B01. Old records
        # retain empty intake metadata; no historical classification is invented.
        columns = {row[1] for row in connection.exec_driver_sql('PRAGMA table_info(document)')}
        if 'intake' not in columns:
            connection.exec_driver_sql("ALTER TABLE document ADD COLUMN intake JSON NOT NULL DEFAULT '{}'")
        case_columns = {row[1] for row in connection.exec_driver_sql('PRAGMA table_info("case")')}
        if 'default_model_id' not in case_columns:
            connection.exec_driver_sql("ALTER TABLE \"case\" ADD COLUMN default_model_id TEXT NOT NULL DEFAULT 'mock-v1'")
        if 'lending_type' not in case_columns:  # papers saved before lending types keep none
            connection.exec_driver_sql('ALTER TABLE "case" ADD COLUMN lending_type TEXT')
        for column, kind in (('deleted_at', 'DATETIME'), ('deleted_by', 'TEXT')):  # papers saved before deletion existed are not deleted
            if column not in case_columns:
                connection.exec_driver_sql(f'ALTER TABLE "case" ADD COLUMN {column} {kind}')
        check_columns = {row[1] for row in connection.exec_driver_sql('PRAGMA table_info(submission_check)')}
        if 'report' not in check_columns:
            connection.exec_driver_sql("ALTER TABLE submission_check ADD COLUMN report JSON NOT NULL DEFAULT '{}'")
        proposal_columns = {row[1] for row in connection.exec_driver_sql('PRAGMA table_info(section_proposal)')}
        if 'payload' not in proposal_columns:
            connection.exec_driver_sql("ALTER TABLE section_proposal ADD COLUMN payload JSON NOT NULL DEFAULT '{}'")
        protected = [c.name for c in models.SectionProposal.__table__.columns
                     if c.name not in {'status', 'resolved_by', 'resolved_at', 'accepted_draft_id'}]
        changed_proposal = ' OR '.join(f'OLD."{name}" IS NOT NEW."{name}"' for name in protected)
        connection.exec_driver_sql(
            'CREATE TRIGGER IF NOT EXISTS immutable_proposal_content BEFORE UPDATE ON section_proposal '
            f"WHEN {changed_proposal} OR OLD.status != 'pending' BEGIN SELECT RAISE(ABORT, 'immutable proposal'); END")
        connection.exec_driver_sql(
            'CREATE TRIGGER IF NOT EXISTS immutable_proposal_delete BEFORE DELETE ON section_proposal '
            "BEGIN SELECT RAISE(ABORT, 'immutable proposal'); END")
        question_columns = [c.name for c in models.ApproverQuestion.__table__.columns
                            if c.name not in {'answer', 'answered_by', 'answered_at', 'resubmitted_es_version_id'}]
        changed_question = ' OR '.join(f'OLD."{name}" IS NOT NEW."{name}"' for name in question_columns)
        connection.exec_driver_sql(
            'CREATE TRIGGER IF NOT EXISTS immutable_question_content BEFORE UPDATE ON approver_question '
            f"WHEN {changed_question} OR OLD.answer IS NOT NULL OR NEW.answer IS NULL "
            "OR trim(NEW.answer) = '' OR NEW.answered_by IS NULL OR NEW.answered_at IS NULL "
            "OR NEW.resubmitted_es_version_id IS NULL BEGIN SELECT RAISE(ABORT, 'immutable question'); END")
        connection.exec_driver_sql(
            'CREATE TRIGGER IF NOT EXISTS immutable_question_delete BEFORE DELETE ON approver_question '
            "BEGIN SELECT RAISE(ABORT, 'immutable question'); END")
        for name in IMMUTABLE:
            table = models.MODEL_BY_NAME[name].__tablename__
            for operation in ('UPDATE', 'DELETE'):
                connection.exec_driver_sql(
                    f'CREATE TRIGGER IF NOT EXISTS immutable_{table}_{operation.lower()} '
                    f'BEFORE {operation} ON "{table}" BEGIN '
                    f"SELECT RAISE(ABORT, 'immutable version'); END"
                )
        immutable_columns = [c.name for c in models.Document.__table__.columns if c.name not in {'confirmed_by', 'confirmed_at', 'conflict_status'}]
        changed = ' OR '.join(f'OLD."{name}" IS NOT NEW."{name}"' for name in immutable_columns)
        connection.exec_driver_sql('DROP TRIGGER IF EXISTS immutable_document_content')
        connection.exec_driver_sql(
            'CREATE TRIGGER IF NOT EXISTS immutable_document_content BEFORE UPDATE ON document '
            f"WHEN {changed} BEGIN SELECT RAISE(ABORT, 'immutable document version'); END"
        )
        connection.exec_driver_sql(
            'CREATE TRIGGER IF NOT EXISTS immutable_document_delete BEFORE DELETE ON document '
            "BEGIN SELECT RAISE(ABORT, 'immutable document version'); END"
        )
    return engine, sessionmaker(bind=engine, expire_on_commit=False)
