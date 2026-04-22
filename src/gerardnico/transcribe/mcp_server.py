# https://github.com/modelcontextprotocol/python-sdk
# https://modelcontextprotocol.io/docs/develop/build-server#importing-packages-and-setting-up-the-instance
# https://gofastmcp.com/getting-started/welcome
from pathlib import Path

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from mcp.types import CallToolResult, TextContent

from gerardnico.transcribe.api import ContextBuilder
from gerardnico.transcribe.transcribe import get_transcript_from_request


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
