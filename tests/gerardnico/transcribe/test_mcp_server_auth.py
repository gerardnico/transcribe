import pytest

from gerardnico.transcribe import mcp_server


def _build_http_scope(path: str, authorization: str | None):
    headers = []
    if authorization is not None:
        headers.append((b"authorization", authorization.encode("latin-1")))
    return {
        "type": "http",
        "path": path,
        "headers": headers,
    }


async def _run_app(app, scope):
    events = []

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(event):
        events.append(event)

    await app(scope, receive, send)
    return events


@pytest.mark.asyncio
async def test_authorized_http_app_returns_401_when_token_missing():
    async def mcp_app(scope, receive, send):
        raise AssertionError("Inner app should not be called")

    app = mcp_server.get_authorized_http_app(
        mcp_app,
        google_client_id="google-client-id",
        authorized_emails={"alice@example.com"},
    )
    events = await _run_app(app, _build_http_scope("/mcp", authorization=None))

    assert events[0]["type"] == "http.response.start"
    assert events[0]["status"] == 401


@pytest.mark.asyncio
async def test_authorized_http_app_returns_401_when_token_invalid(monkeypatch):
    def invalid_token(*args, **kwargs):
        raise ValueError("invalid token")

    monkeypatch.setattr(
        mcp_server.google_id_token,
        "verify_oauth2_token",
        invalid_token,
    )

    async def mcp_app(scope, receive, send):
        raise AssertionError("Inner app should not be called")

    app = mcp_server.get_authorized_http_app(
        mcp_app,
        google_client_id="google-client-id",
        authorized_emails={"alice@example.com"},
    )
    events = await _run_app(app, _build_http_scope("/mcp", authorization="Bearer bad-token"))

    assert events[0]["type"] == "http.response.start"
    assert events[0]["status"] == 401


@pytest.mark.asyncio
async def test_authorized_http_app_returns_403_when_email_not_allowed(monkeypatch):
    def valid_token(*args, **kwargs):
        return {"email": "bob@example.com", "email_verified": True}

    monkeypatch.setattr(
        mcp_server.google_id_token,
        "verify_oauth2_token",
        valid_token,
    )

    async def mcp_app(scope, receive, send):
        raise AssertionError("Inner app should not be called")

    app = mcp_server.get_authorized_http_app(
        mcp_app,
        google_client_id="google-client-id",
        authorized_emails={"alice@example.com"},
    )
    events = await _run_app(app, _build_http_scope("/mcp", authorization="Bearer ok-token"))

    assert events[0]["type"] == "http.response.start"
    assert events[0]["status"] == 403


@pytest.mark.asyncio
async def test_authorized_http_app_passes_when_email_allowed(monkeypatch):
    called = {"value": False}

    def valid_token(*args, **kwargs):
        return {"email": "alice@example.com", "email_verified": True}

    monkeypatch.setattr(
        mcp_server.google_id_token,
        "verify_oauth2_token",
        valid_token,
    )

    async def mcp_app(scope, receive, send):
        called["value"] = True
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    app = mcp_server.get_authorized_http_app(
        mcp_app,
        google_client_id="google-client-id",
        authorized_emails={"alice@example.com"},
    )
    events = await _run_app(app, _build_http_scope("/mcp", authorization="Bearer ok-token"))

    assert called["value"] is True
    assert events[0]["type"] == "http.response.start"
    assert events[0]["status"] == 200
