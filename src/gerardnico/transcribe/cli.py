#!/usr/bin/env python3
"""
Transcript
"""
import logging
from pathlib import Path
from typing import Optional

import typer
from rich.pretty import pprint

from gerardnico.transcribe.api import McpTransport, ContextBuilder, localhost, Context
from gerardnico.transcribe.mcp_server import mcp_run
from gerardnico.transcribe.transcribe import get_transcript_from_request, list_transcripts

typerCli = typer.Typer()

logger = logging.getLogger(__name__)


def print_context(
    context: Context,
):
    """Print the context"""
    pprint(context)
    print("Available Files:")
    assert context.request is not None
    directory = context.request.runtime_directory
    if not directory.exists():
        print("No runtime directory found")
        return
    for item in directory.iterdir():
        item: Path
        if not item.is_file():
            continue
        # print all files
        print(item)


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

    if contextBuilder.print_context:
        print_context(context)
        return

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
    transport: McpTransport = typer.Option(McpTransport.stdio, help="Transport protocol"),
    host: str = typer.Option(localhost, help="Host binding name (0.0.0.0 for world)"),
    port: int = typer.Option(8000, help="Port binding number"),
    origin: str = typer.Option(None, help="The oauth origin"),
):
    """Start a Mcp Server"""
    logger.info(f"{transport.name} Mcp server started")
    contextBuilder: ContextBuilder = ctx.obj
    contextBuilder.transport = transport
    contextBuilder.host = host
    contextBuilder.port = port
    contextBuilder.origin = origin
    context = contextBuilder.build()

    if contextBuilder.print_context:
        print_context(context)
        return

    mcp_run(context.service)


# By default, the callback is only executed before executing a command.
# We use the name main as it's the same in the doc
@typerCli.callback()
def main(
    ctx: typer.Context,
    verbose: bool = typer.Option(False, '-v', '--verbose', help='Verbose mode'),
    home: str | None = typer.Option(None, '--home',
                                    help='The home directory where transcripts and information are stored'),
    print_context_arg: bool | None = typer.Option(False, '--print-context',
                                              help='Print the context and exit')
):
    """
    Transcribe all you want
    """
    # the above comment is shown in the help when no command is asked
    context = ContextBuilder(verbose)
    context.home = home
    context.print_context = print_context_arg
    logger.info(f"About to execute command: {ctx.invoked_subcommand}")
    ctx.obj = context  # user object


def cli():
    """
    Entry point function for the CLI installation used in the pyproject.toml
    """
    typerCli()


if __name__ == '__main__':
    cli()
