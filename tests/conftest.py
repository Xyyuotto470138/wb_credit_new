"""Every test runs offline, including tests in future application blocks."""
import socket
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    monkeypatch.setenv('LLM_PROVIDER', 'mock')

    def forbidden(*args, **kwargs):
        raise AssertionError('Tests must not use network or DNS')

    for method in ('connect', 'connect_ex', 'sendto'):
        monkeypatch.setattr(socket.socket, method, forbidden)
    for method in ('create_connection', 'getaddrinfo', 'gethostbyname', 'gethostbyname_ex', 'gethostbyaddr'):
        monkeypatch.setattr(socket, method, forbidden)


@pytest.fixture
def database(tmp_path):
    from backend.app.database import create_database
    engine, sessions = create_database(tmp_path / 'test.sqlite')
    try:
        with sessions() as session:
            yield session
    finally:
        engine.dispose()
