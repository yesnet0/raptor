"""Security-boundary tests for the Studio FastAPI app."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from packages.studio import app as studio_app


def _request(headers: dict[str, str] | None = None) -> Request:
    raw_headers = [
        (name.lower().encode("latin-1"), value.encode("latin-1"))
        for name, value in (headers or {}).items()
    ]
    return Request({
        "type": "http",
        "method": "POST",
        "scheme": "http",
        "server": ("127.0.0.1", 8765),
        "path": "/settings",
        "headers": raw_headers,
    })


def test_trusted_post_accepts_valid_token_without_browser_metadata():
    studio_app._require_trusted_post(_request(), studio_app._CSRF_TOKEN)


def test_trusted_post_rejects_missing_csrf_token():
    with pytest.raises(HTTPException) as exc:
        studio_app._require_trusted_post(_request(), "")
    assert exc.value.status_code == 403


def test_trusted_post_rejects_cross_site_fetch_metadata():
    with pytest.raises(HTTPException) as exc:
        studio_app._require_trusted_post(
            _request({"Sec-Fetch-Site": "cross-site"}),
            studio_app._CSRF_TOKEN,
        )
    assert exc.value.status_code == 403


def test_trusted_post_rejects_untrusted_origin():
    with pytest.raises(HTTPException) as exc:
        studio_app._require_trusted_post(
            _request({"Origin": "https://attacker.example"}),
            studio_app._CSRF_TOKEN,
        )
    assert exc.value.status_code == 403


def test_trusted_post_accepts_same_origin_header():
    studio_app._require_trusted_post(
        _request({"Origin": "http://127.0.0.1:8765", "Sec-Fetch-Site": "same-origin"}),
        studio_app._CSRF_TOKEN,
    )


def test_post_forms_render_csrf_token():
    template_dir = Path(studio_app.BASE_DIR) / "templates"
    for name in ("new_project.html", "project_new_run.html", "settings.html", "job_detail.html"):
        assert 'name="csrf_token"' in (template_dir / name).read_text()
