import json
from pathlib import Path
import socket

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixture_data():
    def read(name):
        text = (FIXTURES / name).read_text(encoding="utf-8-sig")
        return json.loads(text) if name.endswith(".json") else text
    return read


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def blocked(*args, **kwargs):
        raise AssertionError("Network calls are forbidden in tests")
    monkeypatch.setattr(socket.socket, "connect", blocked)
    monkeypatch.setattr(socket, "create_connection", blocked)
