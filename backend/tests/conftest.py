import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import asyncio
import asyncio.selector_events
import socket
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import app.db as db_module


# Apply event loop policy at module level for broken Windows system
if sys.platform == "win32":
    import selectors

    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    # Monkeypatch _make_self_pipe and _close_self_pipe to work around broken Windows socket subsystem
    def _make_self_pipe_workaround(self):
        """Stub out self-pipe creation for broken Windows socket subsystem."""
        # Set to a marker value that won't be used for actual I/O
        DummySocket = type('DummySocket', (), {
            'fileno': lambda s: -1,
            'send': lambda s, data: len(data),
            'recv': lambda s, bufsize: b'',
            'close': lambda s: None,
        })
        self._ssock = DummySocket()
        self._csock = DummySocket()

    def _close_self_pipe_workaround(self):
        """Stub out self-pipe closing."""
        try:
            if self._ssock is not None:
                self._ssock = None
        except (AttributeError, OSError):
            pass
        try:
            if self._csock is not None:
                self._csock = None
        except (AttributeError, OSError):
            pass

    asyncio.selector_events.BaseSelectorEventLoop._make_self_pipe = _make_self_pipe_workaround
    asyncio.selector_events.BaseSelectorEventLoop._close_self_pipe = _close_self_pipe_workaround

    # Monkeypatch selector._select to handle broken Windows socket subsystem
    _original_selector_select = selectors.SelectSelector._select

    def _select_workaround(self, r, w, _, timeout=None):
        """Workaround for broken Windows select() with empty fd lists."""
        try:
            return _original_selector_select(self, r, w, _, timeout)
        except OSError as e:
            if e.winerror == 10022 and not r and not w:  # Invalid argument + empty lists
                # Just return empty lists to keep event loop going
                return [], [], []
            raise

    selectors.SelectSelector._select = _select_workaround


@pytest.fixture(autouse=True, scope="function")
def _event_loop_policy():
    """Apply event loop policy for Windows."""
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    yield


@pytest.fixture
def db(tmp_path, monkeypatch):
    """Set up test database without TestClient (which uses asyncio)."""
    engine = create_engine(
        f"sqlite:///{tmp_path}/test.db", connect_args={"check_same_thread": False}
    )
    monkeypatch.setattr(db_module, "engine", engine)
    monkeypatch.setattr(db_module, "SessionLocal", sessionmaker(bind=engine, autoflush=False))
    db_module.init_db(target=engine)
    return db_module.SessionLocal()


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Full HTTP client with database setup."""
    engine = create_engine(
        f"sqlite:///{tmp_path}/test.db", connect_args={"check_same_thread": False}
    )
    monkeypatch.setattr(db_module, "engine", engine)
    monkeypatch.setattr(db_module, "SessionLocal", sessionmaker(bind=engine, autoflush=False))
    from app.main import create_app
    return TestClient(create_app())
