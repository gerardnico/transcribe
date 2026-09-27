"""
Transcript
"""
import logging
from pathlib import Path

import typer
from gerardnico.transcribe.api import McpTransport, localhost, Context, CliGlobalOptions
from gerardnico.transcribe.context import context_builder
from gerardnico.transcribe.mcp_server import mcp_run
from gerardnico.transcribe.transcribe import get_transcript_from_request, list_transcripts
from rich.pretty import pprint

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
    lang: str | None = typer.Option(None, '-l', '--lang', help='Language codes (e.g., es,fr) or locale'),
    agent: bool = typer.Option(False, '-a', '--agent', help='Agent mode'),
    download: bool = typer.Option(False, '-ds', '--download-source', help='Download the source video'),
    session_id: str = typer.Option(None, '-sid', '--session-id', help='Browser Session Id Cookie')
):
    """Return a transcript from an audio/video from a URI"""

    global_options: CliGlobalOptions = ctx.obj
    context = context_builder(
        uri=uri,
        lang=lang,
        download_source=download,
        session_id=session_id,
        home=global_options.home_directory,
        verbose=global_options.verbose
    )

    if global_options.print_context:
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
        print(f"\nTranscript file: {response.path}")
        print(f"Transcript files list:")
        list_transcripts(request)

    # Raise if any error
    if response.error is not None and response.error.code != 0:
        logger.error(f"The process has run successfully but an error or warning reporting has been seen")
        raise response.error


@typerCli.command()
def mcp(
    ctx: typer.Context,
    transport: McpTransport = typer.Option(McpTransport.stdio, help="Transport protocol"),
    host: str = typer.Option(localhost, help="Host binding name (0.0.0.0 for world)"),
    port: int = typer.Option(8206, help="Port binding number"),
    origin: str = typer.Option(None, help="The oauth origin"),
):
    """Start a Mcp Server"""
    logger.info(f"{transport.name} Mcp server started")
    global_options: CliGlobalOptions = ctx.obj

    context = context_builder(
        transport=transport,
        host=host,
        port=port,
        origin=origin,
        home=global_options.home_directory,
        verbose=global_options.verbose
    )

    if global_options.print_context:
        print_context(context)
        return

    mcp_run(context.service)


# By default, the callback is only executed before executing a command.
# We use the name main as it's the same in the doc
@typerCli.callback()
def main(
    ctx: typer.Context,
    verbose: bool = typer.Option(False, '-v', '--verbose', help='Verbose mode'),
    home: Path | None = typer.Option(None, '--home',
                                    resolve_path=True,
                                    help='The home directory where transcripts and information are stored'),
    print_context_arg: bool | None = typer.Option(
        False, '--print-context',
        help='Print the context and exit')
):
    """
    Transcribe all you want
    """
    # the above comment is shown in the help when no command is asked
    context = CliGlobalOptions(
        home_directory=home,
        print_context=print_context_arg,
        verbose=verbose
    )
    logger.info(f"About to execute command: {ctx.invoked_subcommand}")
    ctx.obj = context  # user object


def cli():
    """
    Entry point function for the CLI installation used in the pyproject.toml
    """
    typerCli()


if __name__ == '__main__':
    cli()
