#!/usr/bin/env python3
"""
TikTok Transcript Downloader using yt-dlp
Downloads and formats transcripts from TikTok videos
"""
import logging
from typing import Optional

import typer
import uvicorn
from rich.pretty import pprint

from gerardnico.transcribe.api import McpTransport, TranscribeArgs
from gerardnico.transcribe.mcp_server import get_mcp_server
from gerardnico.transcribe.transcribe import build_request, get_transcript_from_request, list_transcripts

typerCli = typer.Typer()

logger = logging.getLogger(__name__)



@typerCli.command()
def info(uri: str = typer.Argument(..., help='URI (URL or file path)')):
    """Get info"""
    cli_args = TranscribeArgs(uri=uri)
    request = build_request(cli_args)
    pprint(request)
    print("Local Transcripts:")
    list_transcripts(request)


@typerCli.command()
def get(uri: str = typer.Argument(..., help='URI (URL or file path)'),
        langs: Optional[str] = typer.Option(None, '-l', '--langs', help='Language codes (e.g., es,fr)'),
        agent: bool = typer.Option(False, '-a', '--agent', help='Agent mode'),
        verbose: bool = typer.Option(False, '-v', '--verbose', help='Verbose mode'),
        download: bool = typer.Option(False, '-ds', '--download-source', help='Download the source video')
        ):
    """Transcribe audio/video from a URI"""

    cli_args = TranscribeArgs(uri=uri, lang=langs, verbose=verbose, download_source=download)
    request = build_request(cli_args)

    response = get_transcript_from_request(request)

    # Result
    is_agent: bool = agent
    if is_agent:
        logger.info(f"The transcript is:")
        actual_transcript_path = response.path
        if actual_transcript_path:
            print(actual_transcript_path.read_text(encoding="utf-8"))
        else:
            raise FileNotFoundError(f"No transcript found at {request.paths.runtime_directory}")
    else:
        logger.info(f"Transcript files:")
        list_transcripts(request)

    # Raise if any error
    if response.error is not None and response.error.code != 0:
        raise response.error


@typerCli.command()
def mcp(transport: McpTransport = typer.Option(McpTransport.stdio, help="Transport protocol")):
    """Start a Mcp Server"""
    logger.info(f"{transport.name} Mcp server started")
    mcpServer = get_mcp_server()
    # Initialize and run the server
    if transport == McpTransport.stdio:
        mcpServer.run(transport="stdio")
        return

    # http://127.0.0.1:8000/mcp
    # same as mcp.run(transport="streamable-http")
    # for https://127.0.0.1:8000/mcp (mandatory)
    # see task cert to generate the certs
    mcp_app = mcpServer.streamable_http_app()  # or mcp.get_asgi_app()
    uvicorn.run(
        mcp_app,
        host="0.0.0.0",
        port=8000,
        ssl_keyfile="./private.key",
        ssl_certfile="./certificate.crt",
    )

def main():
    """Entry point for the CLI"""
    typerCli()

if __name__ == '__main__':
    main()
