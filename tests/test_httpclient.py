"""Tests for the anti-bot HTTP client (kiboy.httpclient).

Locks in the validate_url() fallback contract: a missing or broken curl_cffi
must NOT silently fail every image validation — plain urllib takes over. This
is the regression that zeroed out img_ok in production (every scraped image
was rejected even when og:image was found and valid).

Fully mocked — no network, runs in milliseconds.
"""

import pytest

import kiboy.httpclient as hc


# ---------------------------------------------------------------------------
# _content_type_ok — the shared raster-image gate
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("ct, expected", [
    ("image/jpeg", True),
    ("image/png", True),
    ("image/webp", True),
    ("application/octet-stream", True),
    ("", True),                  # CDNs sometimes omit the header
    ("image/svg+xml", False),    # Pillow can't rasterise SVG
    ("text/html", False),
    ("application/json", False),
])
def test_content_type_ok(ct, expected):
    assert hc._content_type_ok(ct) is expected


# ---------------------------------------------------------------------------
# validate_url — guard clauses (no network reached)
# ---------------------------------------------------------------------------

def test_validate_url_rejects_empty():
    assert hc.validate_url("") is False


def test_validate_url_rejects_non_http():
    assert hc.validate_url("ftp://example.com/x.jpg") is False


def test_validate_url_rejects_svg_extension():
    assert hc.validate_url("https://example.com/logo.svg") is False


def test_validate_url_rejects_blocked_domain():
    # bloomberg.com is in BLOCKED_DOMAINS — rejected before any network call.
    assert hc.validate_url("https://www.bloomberg.com/image.jpg") is False


# ---------------------------------------------------------------------------
# validate_url — urllib fallback when curl_cffi is unavailable
# ---------------------------------------------------------------------------

class _FakeResponse:
    """Minimal stand-in for an http.client.HTTPResponse context manager."""

    def __init__(self, status: int, content_type: str) -> None:
        self.status = status
        self.headers = {"Content-Type": content_type}

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, *exc) -> bool:
        return False


@pytest.fixture
def _no_curl(monkeypatch):
    """Force curl_cffi to look unavailable so the urllib fallback runs."""
    monkeypatch.setattr(hc, "_CURL_CFFI_AVAILABLE", False)
    yield


def _patch_urlopen(monkeypatch, response=None, exc=None):
    """Patch urllib.request.urlopen used by validate_url's fallback path."""
    import urllib.request

    def fake_urlopen(req, timeout=None):
        if exc is not None:
            raise exc
        return response

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)


def test_fallback_accepts_image(_no_curl, monkeypatch):
    _patch_urlopen(monkeypatch, _FakeResponse(200, "image/jpeg"))
    assert hc.validate_url("https://example.com/photo.jpg") is True


def test_fallback_rejects_html(_no_curl, monkeypatch):
    _patch_urlopen(monkeypatch, _FakeResponse(200, "text/html"))
    assert hc.validate_url("https://example.com/page") is False


def test_fallback_rejects_svg_content_type(_no_curl, monkeypatch):
    # URL has no .svg extension, but the server reports SVG → still rejected.
    _patch_urlopen(monkeypatch, _FakeResponse(200, "image/svg+xml"))
    assert hc.validate_url("https://example.com/asset") is False


def test_fallback_rejects_non_200(_no_curl, monkeypatch):
    _patch_urlopen(monkeypatch, _FakeResponse(404, "image/jpeg"))
    assert hc.validate_url("https://example.com/missing.jpg") is False


def test_fallback_handles_network_error(_no_curl, monkeypatch):
    _patch_urlopen(monkeypatch, exc=OSError("connection refused"))
    assert hc.validate_url("https://example.com/photo.jpg") is False
