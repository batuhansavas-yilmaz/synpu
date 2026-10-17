import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from synpu.server.app import create_app, is_allowed_origin


class FakeHistory:
    def series(self, minutes):
        return [{"ts": 1.0, "cpu_usage": 10.0}]


class FakeCollector:
    history = FakeHistory()

    def snapshot(self):
        return {
            "hostname": "pc",
            "timestamp": 123.0,
            "cpu": {"usage_pct": 10.0, "temp_c": 55.0},
            "gpu": None,
            "ram": {"used_mb": 100, "total_mb": 200, "percent": 50.0},
            "fps": {"app": None, "value": None},
        }


@pytest.fixture
def client(tmp_path):
    (tmp_path / "index.html").write_text("<html><body>Synpu</body></html>", encoding="utf-8")
    app = create_app(FakeCollector(), push_interval=0.05, static_dir=tmp_path)
    return TestClient(app)


def test_index_served(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "Synpu" in r.text


def test_snapshot_endpoint_schema(client):
    r = client.get("/api/snapshot")
    assert r.status_code == 200
    d = r.json()
    assert set(d) == {"hostname", "timestamp", "cpu", "gpu", "ram", "fps"}


def test_history_endpoint(client):
    r = client.get("/api/history?minutes=5")
    assert r.status_code == 200
    d = r.json()
    assert d["minutes"] == 5
    assert d["samples"] == [{"ts": 1.0, "cpu_usage": 10.0}]


def test_history_minutes_clamped(client):
    d = client.get("/api/history?minutes=999").json()
    assert d["minutes"] == 60


def test_ws_pushes_snapshot(client):
    with client.websocket_connect("/ws") as ws:
        d = ws.receive_json()
        assert set(d) == {"hostname", "timestamp", "cpu", "gpu", "ram", "fps"}


def test_ws_rejects_public_origin(client):
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect("/ws", headers={"Origin": "https://evil.example"}) as ws:
            ws.receive_json()
    assert exc.value.code == 1008


def test_ws_accepts_private_origin(client):
    with client.websocket_connect("/ws", headers={"Origin": "http://192.168.1.50:8787"}) as ws:
        d = ws.receive_json()
        assert d["hostname"] == "pc"


def test_index_contains_dashboard_ids():
    app = create_app(FakeCollector())
    with TestClient(app) as real_client:
        r = real_client.get("/")
    assert r.status_code == 200
    body = r.text
    assert 'id="val-cpu-usage"' in body
    assert 'id="add-pc"' in body
    assert "synpu.pcs" in body


def test_allowed_origin_regex():
    assert is_allowed_origin(None)
    assert is_allowed_origin("http://localhost:8787")
    assert is_allowed_origin("http://localhost")
    assert is_allowed_origin("http://127.0.0.1:8787")
    assert is_allowed_origin("http://10.0.0.2")
    assert is_allowed_origin("http://172.20.1.1:8787")
    assert is_allowed_origin("http://192.168.1.50:8787")
    assert not is_allowed_origin("http://172.15.1.1")
    assert not is_allowed_origin("http://172.32.0.1")
    assert not is_allowed_origin("https://evil.example")
