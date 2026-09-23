from pathlib import Path

import pytest
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.types import TextContent

from gerardnico.transcribe.api import ContextBuilder, TRANSCRIPT_PREFIX
from gerardnico.transcribe.transcribe import get_transcript_from_request


def test_file_url_request():
    context = (
        ContextBuilder()
        .set_uri("file.mp")
        .build()
    )
    assert context.request.service_name == "file"


def test_tiktok_url_request():
    context = ContextBuilder().set_uri("https://www.tiktok.com/@beanulaegzo/video/7630306225086876959").build()
    assert context.request.service_name == "tiktok"
    assert context.request.runtime_directory == Path(
        f"{context.service.home_directory}/tiktok/beanulaegzo-7630306225086876959")
    assert context.request.file_extension == "mp4"


@pytest.mark.asyncio
async def test_mcp_stdio_command():
    """
    Test MCP server with full protocol
    """

    # We return the transcript file if already present
    # That's what we use to avoid making an external call for now

    # Test in process test
    user_id = "user"
    post_id = "id"
    uri = "https://www.tiktok.com/@%s/video/%s" % (user_id, post_id)
    transcribe_home = Path("./fixtures/home")
    assert transcribe_home.exists(), f"{transcribe_home} does exist"
    context_builder = ContextBuilder()
    context_builder.home = str(transcribe_home)
    context_builder.uri = uri
    context_builder.lang = "eng-US"
    context = context_builder.build()
    if not context.request:
        raise Exception("Request should not be null")
    response = get_transcript_from_request(context.request)
    assert response.error is None
    expected_path = Path(
        transcribe_home,
        "tiktok",
        "%s-%s" % (user_id, post_id),
        TRANSCRIPT_PREFIX + ".subtitle.eng-US.txt")
    assert response.path == expected_path

    # Test cli call - run as a subprocess
    server_params = StdioServerParameters(
        command="uv",
        args=["run", str(Path("../src/gerardnico/transcribe/cli.py")), "--home", str(transcribe_home), "mcp"],
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # List tools
            list_tools_result = await session.list_tools()
            assert len(list_tools_result.tools) == 2

            # Call a tool
            result = await session.call_tool("get_transcript", {"uri": uri, "lang": context.request.lang})
            assert result is not None
            expectedText = "TikTok transcript"
            assert result.content == [TextContent(type="text", text=expectedText)]
