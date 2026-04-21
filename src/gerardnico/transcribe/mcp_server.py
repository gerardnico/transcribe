# https://github.com/PrefectHQ/fastmcp/tree/main/examples
# https://modelcontextprotocol.io/docs/develop/build-server#importing-packages-and-setting-up-the-instance
# https://gofastmcp.com/getting-started/welcome
import uvicorn
from mcp.server.fastmcp import FastMCP

from gerardnico.transcribe.api import McpTransport
from gerardnico.transcribe.cli import CliArgs, build_request, get_transcript_from_request

# Initialize FastMCP server
# The FastMCP class uses Python type hints
# and docstrings to automatically generate tool definitions, making it easy to create and maintain MCP tools.
mcp = FastMCP("transcribe",
              instructions="Provides tools to get transcript from social media video such as TikTok, Twitter, YouTube",
)


@mcp.tool()
async def get_transcript(uri: str) -> str:
    """Get transcript
    Args:
        uri: An uri (URI, URL or file path)
    """
    cli_args = CliArgs(uri=uri)
    request = build_request(cli_args)
    response = get_transcript_from_request(request)
    if not response.error:
        return f"Error: {str(response.error)}"
    if not response.path:
        return f"Error: Sorry, no error were seen but no transcript file was found"
    return response.path.read_text(encoding="utf-8")


def mcp_run(transport: McpTransport):
    # Initialize and run the server
    if transport == McpTransport.stdio:
        mcp.run(transport="stdio")
        return

        # http://127.0.0.1:8000/mcp
    # same as mcp.run(transport="streamable-http")
    # for https://127.0.0.1:8000/mcp (mandatory)
    # see task cert to generate the certs
    app = mcp.streamable_http_app()  # or mcp.get_asgi_app()
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        ssl_keyfile="./private.key",
        ssl_certfile="./certificate.crt",
    )
