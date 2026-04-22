# https://github.com/modelcontextprotocol/python-sdk
# https://modelcontextprotocol.io/docs/develop/build-server#importing-packages-and-setting-up-the-instance
# https://gofastmcp.com/getting-started/welcome
from pathlib import Path

import uvicorn
from google.auth.transport.requests import Request as GoogleAuthRequest
from google.oauth2 import id_token as google_id_token
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from mcp.types import CallToolResult, TextContent

from gerardnico.transcribe.api import ContextBuilder, McpTransport, Service
from gerardnico.transcribe.transcribe import get_transcript_from_request


def _response_body(status: int, body: str):
    return [
        {
            "type": "http.response.start",
            "status": status,
            "headers": [(b"content-type", b"text/plain; charset=utf-8")],
        },
        {"type": "http.response.body", "body": body.encode("utf-8")},
    ]


def get_authorized_http_app(mcp_app, google_client_id: str, authorized_emails: set[str]):
    async def authorized_app(scope, receive, send):
        if scope["type"] != "http":
            await mcp_app(scope, receive, send)
            return

        path = scope.get("path", "")
        if not path.startswith("/mcp"):
            await mcp_app(scope, receive, send)
            return

        headers = {
            key.decode("latin-1").lower(): value.decode("latin-1")
            for key, value in scope.get("headers", [])
        }
        auth_header = headers.get("authorization", "")
        if not auth_header.startswith("Bearer "):
            for event in _response_body(401, "Missing Authorization Bearer token"):
                await send(event)
            return

        token = auth_header[len("Bearer "):].strip()
        if not token:
            for event in _response_body(401, "Missing Authorization Bearer token"):
                await send(event)
            return

        try:
            claims = google_id_token.verify_oauth2_token(
                token,
                GoogleAuthRequest(),
                google_client_id,
            )
        except ValueError:
            for event in _response_body(401, "Invalid Google ID token"):
                await send(event)
            return

        email = str(claims.get("email", "")).strip().lower()
        is_email_verified = bool(claims.get("email_verified"))
        if not is_email_verified or email not in authorized_emails:
            for event in _response_body(403, "Forbidden: user email is not authorized"):
                await send(event)
            return

        await mcp_app(scope, receive, send)

    return authorized_app


def get_mcp_server(home: Path):
    # Initialize FastMCP server
    # The FastMCP class uses Python type hints
    # and docstrings to automatically generate tool definitions, making it easy to create and maintain MCP tools.
    mcp = FastMCP(
        "transcribe",
        instructions="Provides tools to get a transcript from a social media video such as TikTok, Twitter, YouTube",
    )

    @mcp.tool()
    async def get_transcript(uri: str) -> CallToolResult:
        """Get transcript
        Args:
            uri: An uri (URI, URL or file path)
        """
        contextBuilder = ContextBuilder()
        contextBuilder.home = str(home)
        contextBuilder.uri = uri
        context = contextBuilder.build()
        if not context.request:
            raise Exception("Internal exception, the context should have a request object")
        response = get_transcript_from_request(context.request)
        # https://py.sdk.modelcontextprotocol.io/server/#error-handling
        if response.error:
            raise ToolError(f"{str(response.error)}")
        if not response.path:
            raise ToolError("Sorry, no errors were seen but no transcript file was found")
        return CallToolResult(
            content=[TextContent(type="text", text=response.path.read_text(encoding="utf-8"))],
        )

    return mcp


def mcp_run(service: Service):
    mcpServer = get_mcp_server(service.home_directory)
    # Initialize and run the server
    if service.mcp_transport == McpTransport.stdio:
        mcpServer.run(transport="stdio")
        return

    # http://127.0.0.1:8000/mcp
    # same as mcp.run(transport="streamable-http")
    # for https://127.0.0.1:8000/mcp (mandatory)
    # see task cert to generate the certs
    mcp_app = mcpServer.streamable_http_app()  # or mcp.get_asgi_app()
    assert service.oauth2_client_id is not None
    assert service.oauth2_authorized_emails is not None
    authorized_mcp_app = get_authorized_http_app(
        mcp_app,
        google_client_id=service.oauth2_client_id,
        authorized_emails=service.oauth2_authorized_emails,
    )
    uvicorn.run(
        authorized_mcp_app,
        host="0.0.0.0",
        port=8000,
        ssl_keyfile="./private.key",
        ssl_certfile=service.ssl_cert_file,
    )
