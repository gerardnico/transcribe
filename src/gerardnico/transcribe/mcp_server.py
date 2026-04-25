# https://github.com/modelcontextprotocol/python-sdk
# https://modelcontextprotocol.io/docs/tutorials/security/authorization
# https://modelcontextprotocol.io/docs/develop/build-server#importing-packages-and-setting-up-the-instance
# https://gofastmcp.com/getting-started/welcome
import logging

import uvicorn
from fastapi import FastAPI
from fastmcp import FastMCP
from fastmcp.server.auth.providers.google import GoogleProvider
from mcp.server.fastmcp.exceptions import ToolError
from pydantic import Field

from gerardnico.transcribe.api import ContextBuilder, McpTransport, Service
from gerardnico.transcribe.transcribe import get_transcript_from_request

logger = logging.getLogger(__name__)


def get_mcp_server(service: Service):
    # Initialize FastMCP server
    # The FastMCP class uses Python type hints
    # and docstrings to automatically generate tool definitions

    auth = None
    if service.mcp_transport == McpTransport.http and service.oauth2_client_id:
        # Doc: https://gofastmcp.com/integrations/google
        # Sdk: https://gofastmcp.com/python-sdk/fastmcp-server-auth-providers-google
        assert service.oauth2_client_secret is not None
        if service.oauth2_client_id and not service.oauth2_client_secret:
            logger.warning("The oauth2_client_secret is empty while the oauth2_client_id is not. Oauth may not work")
        assert service.oauth2_origin is not None
        logger.info(f"Oauth enabled with origin url {service.oauth2_origin}")
        auth = GoogleProvider(
            client_id=service.oauth2_client_id,
            client_secret=service.oauth2_client_secret,
            # Base_url: must match the OAuth configuration: Authorized JavaScript origins
            base_url=service.oauth2_origin,
            # Request user information
            required_scopes=[
                "openid",
                "https://www.googleapis.com/auth/userinfo.email",
            ],
        )

    # https://gofastmcp.com/servers/server#identity
    mcp = FastMCP(
        "transcribe",
        instructions="Provides tools to get a transcript from a social media video such as TikTok, Twitter, YouTube",
        website_url="https://github.com/gerardnico/transcribe",
        # for icons, see https://github.com/modelcontextprotocol/python-sdk/blob/main/examples/mcpserver/icons_demo.py
        auth=auth
    )

    @mcp.tool()
    async def get_transcript(
        uri: str = Field(description="The uri of the resource to transcribe"),
        lang: str|None = Field(description="The lang of transcript")
    ) -> str:
        """Get a transcript from a resource"""
        contextBuilder = ContextBuilder()
        contextBuilder.home = str(service.home_directory)
        contextBuilder.uri = uri
        contextBuilder.lang = lang
        context = contextBuilder.build()
        if not context.request:
            raise Exception("Internal exception, the context should have a request object")
        response = get_transcript_from_request(context.request)
        # https://py.sdk.modelcontextprotocol.io/server/#error-handling
        if not response.path:
            if not response.error:
                raise ToolError(f"Sorry, no transcript file was found and no errors were seen.")
            else:
                # yt-dlp may send an error even if the subtitle is there
                # so if we have a path, we don't have any error
                #
                # An error may just be that the user needs to log in because the content is flagged as being not public
                # Example: TikTok: This post may not be comfortable for some audiences. Log in for access.
                raise ToolError(f"Sorry, an error has occurred: {str(response.error)}")

        # We don't return a CallToolResult object
        # becuase it is persisted as JSON in the text field, making it difficult to test
        # return CallToolResult(
        #     content=[TextContent(type="text", text="")],
        # )
        return response.path.read_text(encoding="utf-8")

    @mcp.tool
    async def get_user_info() -> dict:
        """Returns information about the authenticated user."""
        from fastmcp.server.dependencies import get_access_token
        token = get_access_token()
        if not token:
            return {
                "subject": "anonymous",
            }
        # The JWT token claims
        return {
            "subject": token.claims.get("sub"),
            "email": token.claims.get("email"),
            "name": token.claims.get("name"),
            "picture": token.claims.get("picture"),
            "locale": token.claims.get("locale")
        }

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
    mcp_app = mcp_server.http_app(path="/mcp")
    fast_api_app = FastAPI(lifespan=mcp_app.lifespan)

    # api sub-route is mandatory to note class with the
    # mcp standard route: https://gofastmcp.com/deployment/http#route-types
    @fast_api_app.get("/api/health")
    def health():
        return {"status": "ok"}

    # Mount MCP at /
    # it's mandatory to get the oauth well-known path
    # such as: http://localhost:8206/.well-known/oauth-authorization-server
    # see https://gofastmcp.com/deployment/http#mounting-authenticated-servers
    fast_api_app.mount("/", mcp_app)

    # http://127.0.0.1:8206/mcp
    # for https://127.0.0.1:8206/mcp (mandatory)
    # see task cert to generate the certs
    logger.info(f"Starting Streamable Http Mcp server at {service.binding_host}:{service.binding_port}")
    logger.debug(f"ssl cert file is {service.ssl_cert_file}")
    logger.debug(f"ssl key file is {service.ssl_key_file}")
    logger.debug(f"host is {service.binding_host}")
    uvicorn.run(
        fast_api_app,
        host=service.binding_host,
        port=service.binding_port,
        # ssl_keyfile=service.ssl_key_file,
        # ssl_certfile=service.ssl_cert_file,
    )
