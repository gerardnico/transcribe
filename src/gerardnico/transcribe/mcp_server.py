# https://github.com/modelcontextprotocol/python-sdk
# https://github.com/PrefectHQ/fastmcp/tree/main/examples
# https://modelcontextprotocol.io/docs/develop/build-server#importing-packages-and-setting-up-the-instance
# https://gofastmcp.com/getting-started/welcome
from mcp.server.fastmcp import FastMCP

from gerardnico.transcribe.api import ContextBuilder
from gerardnico.transcribe.transcribe import get_transcript_from_request


def get_mcp_server():
    # Initialize FastMCP server
    # The FastMCP class uses Python type hints
    # and docstrings to automatically generate tool definitions, making it easy to create and maintain MCP tools.
    mcp = FastMCP(
        "transcribe",
        instructions="Provides tools to get a transcript from a social media video such as TikTok, Twitter, YouTube",
    )

    @mcp.tool()
    async def get_transcript(uri: str) -> str:
        """Get transcript
        Args:
            uri: An uri (URI, URL or file path)
        """
        contextBuilder = ContextBuilder()
        contextBuilder.uri=uri
        context = contextBuilder.build()
        response = get_transcript_from_request(context)
        if not response.error:
            return f"Error: {str(response.error)}"
        if not response.path:
            return f"Error: Sorry, no error were seen but no transcript file was found"
        return response.path.read_text(encoding="utf-8")

    return mcp


