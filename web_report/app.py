"""Minimal Flask dashboard for Self-Awaken audit runs."""

from __future__ import annotations

import json
from pathlib import Path

from flask import Flask, abort, render_template, send_file

app = Flask(__name__)
RUNS_DIR = Path(__file__).resolve().parent.parent / "runs"


def _resolve_run_path(run_id: str) -> Path:
    safe_id = Path(run_id).name
    if not safe_id:
        abort(404)
    candidates = [
        RUNS_DIR / f"{safe_id}.json",
        RUNS_DIR / safe_id,
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    abort(404)


@app.route("/")
def index():
    runs = sorted(RUNS_DIR.glob("*.json")) if RUNS_DIR.is_dir() else []
    return render_template(
        "index.html",
        runs=[path.stem for path in runs],
    )


@app.route("/report/<run_id>")
def report(run_id: str):
    path = _resolve_run_path(run_id)
    with path.open("r", encoding="utf-8") as handle:
        run_data = json.load(handle)
    md_path = path.with_suffix(".md")
    markdown_report = md_path.read_text(encoding="utf-8") if md_path.is_file() else None
    return render_template(
        "report.html",
        run_id=run_id,
        run=run_data,
        markdown_report=markdown_report,
    )


@app.route("/report/<run_id>/download.json")
def download_json(run_id: str):
    path = _resolve_run_path(run_id)
    return send_file(path, as_attachment=True, download_name=f"{run_id}.json")


@app.route("/report/<run_id>/download.md")
def download_md(run_id: str):
    path = _resolve_run_path(run_id)
    md_path = path.with_suffix(".md")
    if not md_path.is_file():
        abort(404)
    return send_file(md_path, as_attachment=True, download_name=f"{run_id}.md")


if __name__ == "__main__":
    app.run(debug=True)
