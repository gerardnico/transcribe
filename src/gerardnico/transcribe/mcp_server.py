# https://github.com/modelcontextprotocol/python-sdk
# https://modelcontextprotocol.io/docs/tutorials/security/authorization
# https://modelcontextprotocol.io/docs/develop/build-server#importing-packages-and-setting-up-the-instance
# https://gofastmcp.com/getting-started/welcome
import logging

import uvicorn
from fastapi import FastAPI
from fastmcp import FastMCP
from google.auth.transport.requests import Request as GoogleAuthRequest
from google.oauth2 import id_token as google_id_token
from mcp.server.auth.provider import TokenVerifier, AccessToken
from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp.exceptions import ToolError
from mcp.types import CallToolResult, TextContent
from pydantic import Field, AnyHttpUrl

from gerardnico.transcribe.api import ContextBuilder, McpTransport, Service
from gerardnico.transcribe.transcribe import get_transcript_from_request

logger = logging.getLogger(__name__)


class SimpleTokenVerifier(TokenVerifier):
    """Simple token verifier for demonstration."""
    authorized_emails: set[str]

    def __init__(self, emails: set[str], google_client_id: str, client_secret: str):
        self.authorized_emails = emails
        self.google_client_id = google_client_id
        self.client_secret = client_secret

    async def verify_token(self, token: str) -> AccessToken | None:
        claims = google_id_token.verify_oauth2_token(
            token,
            GoogleAuthRequest(),
            self.google_client_id,
        )

        email = str(claims.get("email", "")).strip().lower()
        is_email_verified = bool(claims.get("email_verified"))
        if not is_email_verified or email not in self.authorized_emails:
            raise Exception(f"Email {email} is not authorized, bad email")

        return AccessToken(
            token=token,
            client_id=claims.get("client_id", "unknown"),
            scopes=claims.get("scope", "").split() if claims.get("scope") else [],
            expires_at=claims.get("exp"),
            resource=claims.get("aud"),  # Include resource in token
        )


def get_mcp_server(service: Service):
    # Initialize FastMCP server
    # The FastMCP class uses Python type hints
    # and docstrings to automatically generate tool definitions, making it easy to create and maintain MCP tools.

    auth_settings = None
    token_verifier = None
    if service.mcp_transport == McpTransport.http:
        assert service.oauth2_client_id is not None
        assert service.oauth2_authorized_emails is not None
        # Data found in .well-known/oauth-protected-resource/mcp
        auth_settings = AuthSettings(
            # Google issuer (where tokens come from)
            issuer_url=AnyHttpUrl("https://accounts.google.com"),
            # Your MCP resource URL
            resource_server_url=AnyHttpUrl(f"http://{service.host}:8000/mcp"),
            # Optional scopes your server expects
            required_scopes=["openid", "email", "profile"],
            # Metadata for OAuth client registration (MCP clients)
            client_registration_options={
                "token_endpoint_auth_method": "none",
                "grant_types": ["authorization_code", "refresh_token"],
                "response_types": ["code"],
                "redirect_uris": [
                    "http://localhost:6274/oauth/callback",
                    "http://127.0.0.1:6274/oauth/callback",
                ],
                "scope": "openid email profile",
            },
        )
        token_verifier = SimpleTokenVerifier(
            emails=service.oauth2_authorized_emails,
            google_client_id=service.oauth2_client_id,
            client_secret="yolo"
        )

    # https://gofastmcp.com/servers/server#identity
    mcp = FastMCP(
        "transcribe",
        instructions="Provides tools to get a transcript from a social media video such as TikTok, Twitter, YouTube",
        website_url="https://github.com/gerardnico/transcribe",
        # for icons, see https://github.com/modelcontextprotocol/python-sdk/blob/main/examples/mcpserver/icons_demo.py
    )

    @mcp.tool()
    async def get_transcript(uri: str = Field(description="The uri of the resource to transcribe")) -> CallToolResult:
        """Get a transcript from a resource"""
        contextBuilder = ContextBuilder()
        contextBuilder.home = str(service.home_directory)
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
    mcp_server = get_mcp_server(service)

    # stdio
    if service.mcp_transport == McpTransport.stdio:
        logger.info(f"Starting stdio McpServer")
        mcp_server.run(transport="stdio")
        return

    # http
    # Fast Api and Fast Mcp based on https://gofastmcp.com/deployment/http#fastapi-integration
    # Create FastAPI app with MCP lifespan (required for session management)
    # Create the MCP ASGI app with path="/" since we'll mount at /mcp
    mcp_app = mcp_server.http_app(path="/")
    fast_api_app = FastAPI(lifespan=mcp_app.lifespan)

    # api sub-route is mandatory to note class with the
    # mcp standard route: https://gofastmcp.com/deployment/http#route-types
    @fast_api_app.get("/api/health")
    def health():
        return {"status": "ok"}

    # Mount MCP at /mcp
    fast_api_app.mount("/mcp", mcp_app)

    # http://127.0.0.1:8000/mcp
    # for https://127.0.0.1:8000/mcp (mandatory)
    # see task cert to generate the certs
    port = 8000
    logger.info(f"Starting Streamable Http Mcp server at {service.host}:{port}")
    logger.debug(f"ssl cert file is {service.ssl_cert_file}")
    logger.debug(f"ssl key file is {service.ssl_key_file}")
    logger.debug(f"host is {service.host}")
    uvicorn.run(
        fast_api_app,
        host=service.host,
        port=port,
        # ssl_keyfile=service.ssl_key_file,
        # ssl_certfile=service.ssl_cert_file,
    )
