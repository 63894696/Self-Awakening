import json
from pathlib import Path

import pytest

flask = pytest.importorskip("flask")

from web_report.app import RUNS_DIR, app  # noqa: E402


@pytest.fixture
def client(tmp_path, monkeypatch):
    runs = tmp_path / "runs"
    runs.mkdir()
    sample = {
        "kind": "run",
        "requested_model": "test/model",
        "endpoint": "https://api.example.com/v1",
        "created_at": "2026-01-01T00:00:00+00:00",
        "summary": {"accuracy": 0.5, "avg_latency_ms": 100, "error_count": 1},
        "results": [
            {
                "probe_id": "math-001",
                "category": "math",
                "score": 1.0,
                "latency_ms": 120,
                "error": None,
            }
        ],
    }
    (runs / "demo-run.json").write_text(json.dumps(sample), encoding="utf-8")
    monkeypatch.setattr("web_report.app.RUNS_DIR", runs)
    app.config["TESTING"] = True
    return app.test_client()


def test_index_lists_runs(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"demo-run" in response.data


def test_report_page(client):
    response = client.get("/report/demo-run")
    assert response.status_code == 200
    assert b"test/model" in response.data
    assert b"math-001" in response.data


def test_download_json(client):
    response = client.get("/report/demo-run/download.json")
    assert response.status_code == 200
    payload = json.loads(response.data)
    assert payload["requested_model"] == "test/model"


def test_download_md_missing(client):
    response = client.get("/report/demo-run/download.md")
    assert response.status_code == 404
