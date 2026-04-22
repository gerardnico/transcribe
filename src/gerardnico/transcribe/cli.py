#!/usr/bin/env python3
"""
TikTok Transcript Downloader using yt-dlp
Downloads and formats transcripts from TikTok videos
"""
import logging
from typing import Optional

import typer
from rich.pretty import pprint

from gerardnico.transcribe.api import McpTransport, ContextBuilder
from gerardnico.transcribe.mcp_server import mcp_run
from gerardnico.transcribe.transcribe import get_transcript_from_request, list_transcripts

typerCli = typer.Typer()

logger = logging.getLogger(__name__)


@typerCli.command()
def info(
    ctx: typer.Context,
    uri: str = typer.Argument(..., help='URI (URL or file path)')
):
    """Get information about a transcript"""
    contextBuilder: ContextBuilder = ctx.obj
    contextBuilder.uri = uri
    context = contextBuilder.build()
    pprint(context)
    print("Local Transcripts:")
    assert context.request is not None
    list_transcripts(context.request)


@typerCli.command()
def get(
    ctx: typer.Context,
    uri: str = typer.Argument(..., help='URI (URL or file path)'),
    langs: Optional[str] = typer.Option(None, '-l', '--langs', help='Language codes (e.g., es,fr)'),
    agent: bool = typer.Option(False, '-a', '--agent', help='Agent mode'),
    download: bool = typer.Option(False, '-ds', '--download-source', help='Download the source video')
):
    """Return a transcript from an audio/video from a URI"""
    contextBuilder: ContextBuilder = ctx.obj
    contextBuilder.uri = uri
    contextBuilder.lang = langs
    contextBuilder.download_source = download
    context = contextBuilder.build()
    request = context.request
    assert request is not None
    response = get_transcript_from_request(request)

    # Result
    is_agent: bool = agent
    if is_agent:
        logger.info(f"The transcript is:")
        actual_transcript_path = response.path
        if actual_transcript_path:
            print(actual_transcript_path.read_text(encoding="utf-8"))
        else:
            raise FileNotFoundError(f"No transcript found at {request.runtime_directory}")
    else:
        logger.info(f"Transcript files:")
        list_transcripts(request)

    # Raise if any error
    if response.error is not None and response.error.code != 0:
        raise response.error


@typerCli.command()
def mcp(
    ctx: typer.Context,
    transport: McpTransport = typer.Option(McpTransport.stdio, help="Transport protocol")):
    """Start a Mcp Server"""
    logger.info(f"{transport.name} Mcp server started")
    contextBuilder: ContextBuilder = ctx.obj
    contextBuilder.transport = transport
    context = contextBuilder.build()
    mcp_run(context.service)


# By default, the callback is only executed before executing a command.
# We use the name main as it's the same in the doc
@typerCli.callback()
def main(
    ctx: typer.Context,
    verbose: bool = typer.Option(False, '-v', '--verbose', help='Verbose mode'),
    home: str | None = typer.Option(None, '--home',
                                    help='The home directory where transcripts and information are stored')
):
    """
    Transcribe all you want
    """
    # the above comment is shown in the help when no command is asked
    context = ContextBuilder(verbose)
    context.home = home
    logger.info(f"About to execute command: {ctx.invoked_subcommand}")
    ctx.obj = context  # user object


def cli():
    """
    Entry point function for the CLI installation used in the pyproject.toml
    """
    typerCli()


if __name__ == '__main__':
    cli()
