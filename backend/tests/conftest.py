import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import app.db as db_module


def pytest_configure(config):
    """Fix Windows asyncio socketpair issue before tests run."""
    if sys.platform == "win32":
        import asyncio
        import socket as socket_module

        # Store original socketpair
        _orig_socketpair = socket_module.socketpair

        def _socket_pair_wrapper(*args, **kwargs):
            """Wrap socketpair to handle Windows socket issues."""
            try:
                return _orig_socketpair(*args, **kwargs)
            except OSError:
                # Fallback to creating socket pair manually if socketpair fails
                import socket
                lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                lsock.bind(("127.0.0.1", 0))
                lsock.listen(1)
                csock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                try:
                    csock.connect(lsock.getsockname())
                    ssock, _ = lsock.accept()
                    lsock.close()
                    return ssock, csock
                except:
                    lsock.close()
                    csock.close()
                    raise

        # Monkey patch socket.socketpair
        socket_module.socketpair = _socket_pair_wrapper


@pytest.fixture
def client(tmp_path, monkeypatch):
    engine = create_engine(
        f"sqlite:///{tmp_path}/test.db", connect_args={"check_same_thread": False}
    )
    db_module.Base.metadata.create_all(engine)
    monkeypatch.setattr(db_module, "engine", engine)
    monkeypatch.setattr(db_module, "SessionLocal", sessionmaker(bind=engine, autoflush=False))
    from app.main import create_app
    return TestClient(create_app())
