import os
from pathlib import Path

import pytest
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from gerardnico.transcribe.api import TranscribeArgs
from gerardnico.transcribe.transcribe import build_request


def test_file_url_request():
    cli_args = TranscribeArgs(uri="file.mp3")
    request = build_request(cli_args)
    assert request.service_name == "file"


def test_tiktok_url_request():
    cli_args = TranscribeArgs(uri="https://www.tiktok.com/@beanulaegzo/video/7630306225086876959")
    request = build_request(cli_args)
    assert request.service_name == "tiktok"
    home = os.environ.get('TRANSCRIBE_HOME')
    if not home:
        home = f"{os.environ.get('HOME')}/.transcribe"
    assert request.paths.runtime_directory == Path(f"{home}/tiktok/beanulaegzo-7630306225086876959")
    assert request.paths.file_extension == "mp4"


@pytest.mark.asyncio
async def test_mcp_stdio_command():
    """Test MCP server with full protocol."""
    # Run as a subprocess
    server_params = StdioServerParameters(
        command="uv",
        args=["run", str(Path("src/gerardnico/transcribe/cli.py")), "mcp"],
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # List tools
            list_tools_result = await session.list_tools()
            assert len(list_tools_result.tools) == 1

            # Call a tool
            # result = await session.call_tool("get_transcript", {"uri": "test"})
            # assert result is not None
