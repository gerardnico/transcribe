#!/usr/bin/env python3
"""
TikTok Transcript Downloader using yt-dlp
Downloads and formats transcripts from TikTok videos
"""
import argparse
import logging
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import typer
import webvtt
from rich.pretty import pprint

from gerardnico.transcribe.api import Request, Paths, McpTransport, Response
from gerardnico.transcribe.mcp_server import mcp_run

app = typer.Typer()

from gerardnico.transcribe.ffmpeg import video_to_audio
from gerardnico.transcribe.social import execute_yt_dlp
from gerardnico.transcribe.whisper import post_processing_transcribe_audio_to_text

logger = logging.getLogger(__name__)


def _require_dependency(pkg: str, version: str):
    """To verify dependency"""
    from importlib.metadata import version as v
    from packaging.version import Version

    installed = Version(v(pkg))
    required = Version(version)

    if installed != required:
        raise RuntimeError(
            f"[Dependency error] {pkg}=={required} required, "
            f"but {installed} is installed"
        )


@dataclass
class Context:
    request: Request


@dataclass
class CliArgs:
    uri: str
    lang: Optional[str] = field(default=None)
    verbose: bool = field(default=False)
    download: bool = field(default=False)


def clean_duplicate_lines(lines):
    """Remove consecutive duplicate lines"""
    if not lines:
        return []

    cleaned = [lines[0]]
    for line in lines[1:]:
        if line.strip() and line.strip() != cleaned[-1].strip():
            cleaned.append(line)
    return cleaned


def detect_paragraphs(lines, time_gap_threshold=2.0):
    """
    Detect paragraph breaks based on timing gaps
    Returns list of paragraphs (each paragraph is a list of lines)
    """
    if not lines:
        return []

    paragraphs = []
    current_paragraph = []

    for i, line in enumerate(lines):
        current_paragraph.append(line['text'])

        # Check if there's a significant time gap to next line
        if i < len(lines) - 1:
            time_gap = lines[i + 1]['start'] - line['end']
            if time_gap > time_gap_threshold:
                # End current paragraph
                paragraphs.append(current_paragraph)
                current_paragraph = []

    # Add the last paragraph
    if current_paragraph:
        paragraphs.append(current_paragraph)

    return paragraphs


def format_transcript(subtitles, include_timestamps=False, detect_para=True):
    """
    Format transcript with optional timestamps and paragraph detection
    """
    if not subtitles:
        return "No transcript available"

    # Parse subtitle data
    lines = []
    for item in subtitles:
        if 'text' in item and item['text'].strip():
            lines.append({
                'text': item['text'].strip(),
                'start': item.get('start', 0),
                'end': item.get('end', 0)
            })

    if not lines:
        return "No transcript content found"

    # Remove duplicates first
    unique_lines = []
    seen = set()
    for line in lines:
        text = line['text'].lower()
        if text not in seen:
            seen.add(text)
            unique_lines.append(line)

    if include_timestamps:
        # Format with timestamps
        result = []
        for line in unique_lines:
            timestamp = format_timestamp(line['start'])
            result.append(f"[{timestamp}] {line['text']}")
        return '\n'.join(result)
    else:
        # Format without timestamps
        if detect_para:
            # Detect paragraphs based on timing
            paragraphs = detect_paragraphs(unique_lines)
            # Join lines within paragraphs with space, separate paragraphs with double newline
            formatted_paragraphs = [' '.join(para) for para in paragraphs]
            return '\n\n'.join(formatted_paragraphs)
        else:
            # Simple line-by-line format
            return '\n'.join([line['text'] for line in unique_lines])


def format_timestamp(seconds):
    """Convert seconds to MM:SS format"""
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes:02d}:{secs:02d}"


# Custom parser to print the help (not the small usage)
class ArgumentParserNoUsage(argparse.ArgumentParser):
    def error(self, message):
        # Print the error message and the help (not the usage)
        # https://docs.python.org/3.11/library/argparse.html#printing-help
        print(f'\nerror: {message}', self.format_help(), sep='\n\n', file=sys.stderr)
        sys.exit(2)


from urllib.parse import urlparse, parse_qs, ParseResult


def post_processing_vtt(vtt_file_path: Path) -> None:
    """
    Process a single VTT file using the webvtt library.

    Args:
        vtt_file_path: Path to the VTT file
    """
    try:
        # Parse the VTT file
        vtt = webvtt.read(str(vtt_file_path))

        # Extract all text from captions
        text_lines = []
        for caption in vtt:
            # Get the text and strip whitespace
            text = caption.text.strip()
            if text:
                text_lines.append(text)

        # Create output filename with .txt extension
        output_file = vtt_file_path.with_suffix('.txt')

        # Write the cleaned text to file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(text_lines))

        logger.info(f"Processed: {vtt_file_path.name} -> {output_file.name}")

    except Exception as e:
        logger.error(f"Error processing {vtt_file_path.name}: {e}")


def get_transcription(context, vtt_file_count):
    if not vtt_file_count == 0:
        logger.debug(f"  * Subtitle file found, no transcription")
        return False
    if context.paths.type != "video":
        logger.debug(f"  * Not a video mode, no transcription")
        return False
    if not Path(context.paths.video_path).exists():
        logger.debug(f"  * Video is not present, no transcription")
        return False
    return True


def post_processing(request: Request) -> None:
    """
    Scan all files in a directory
    * extract clean text, and save as .txt files.
    * transcribe if needed

    Args:
        request: The context object
    """
    directory = request.paths.runtime_directory
    directory_path = Path(directory)

    if not directory_path.exists():
        raise ValueError(f"Runtime Directory does not exist: {directory}")

    vtt_file_count = 0
    for item in directory_path.iterdir():
        # Check if it's a file and has .vtt extension
        if item.is_file() and item.suffix.lower() == '.vtt':
            post_processing_vtt(item)
            vtt_file_count += 1

    if vtt_file_count == 0:
        logger.info(f"No .vtt files found in {directory}")
    else:
        logger.info(f"Processed {vtt_file_count} VTT file(s)")

    logger.info(f"Trying to transcribe")
    if get_transcription(request, vtt_file_count):
        video_to_audio(request)
        post_processing_transcribe_audio_to_text(request)


def build_request(cli_args: CliArgs) -> Request:
    parsed_uri: ParseResult = urlparse(cli_args.uri)
    if not parsed_uri.scheme or parsed_uri.scheme == "file":
        service_name = "file"
    else:
        apex_name = parsed_uri.netloc  # authority

        # remove www. if present
        if apex_name.startswith("www."):
            apex_name = apex_name[4:]

        # service name is the first part before the dot
        service_name = apex_name.split('.')[0]

    # default id is empty
    id_value = ""

    # YouTube URL handling
    if service_name == "youtube":
        # YouTube video ID is usually in the 'v' query parameter
        query_params = parse_qs(parsed_uri.query)
        id_value = query_params.get('v', [''])[0]
    # TikTok URL handling
    elif service_name == "tiktok":
        # TikTok ID is made of username (without @) + last part of path
        path_parts = [p for p in parsed_uri.path.split('/') if p]
        if len(path_parts) != 3 or (not path_parts[0].startswith('@')) or path_parts[1] != 'video':
            raise ValueError("The tiktok url is not valid")
        username = path_parts[0][1:]  # remove @
        video_id = path_parts[2]
        id_value = f"{username}-{video_id}"
    elif service_name == "x" or service_name == "twitter":
        # https://x.com/forrestpknight/status/2012561898097594545
        path_parts = [p for p in parsed_uri.path.split('/') if p]
        if len(path_parts) != 3 and path_parts[1] != 'status':
            raise ValueError("The x url is not valid")
        username = path_parts[0]
        video_id = path_parts[2]
        id_value = f"{username}-{video_id}"
    elif service_name == "file":
        id_value = f'{parsed_uri.path}'
    else:
        raise ValueError(f"{service_name} not yet supported")

    # Determine the runtime directory (download for social url)
    # Note that if we want to add a timestamp, we
    # * need to get the info.json first
    # or, we can add `%(upload_date>%Y-%m-%d)s` in a template
    transcribe_home = os.environ.get('TRANSCRIBE_HOME')
    if not transcribe_home:
        transcribe_home = os.environ.get('HOME') + "/.transcribe"
    runtime_directory = Path(f"{transcribe_home}/{service_name}/{id_value}")

    # orig is a lang suffix of YouTube
    # it the video is in nl, you get 2 subtitles, `nl` and `nl-orig`
    orig = "orig"
    if cli_args.lang is None:
        if service_name == "youtube":
            langs = [orig]
        else:
            # we let yt-dlp decide, normally the spoken language of the video
            langs = None
    else:
        langs = cli_args.lang.split(",")

    # Compute derived properties
    # file type
    if parsed_uri.scheme != 'file':
        # social media request
        file_extension = "mp4"
        file_name = f"video.{file_extension}"
        video_path = Path(f"{runtime_directory}/{file_name}")
        audio_path = Path(f"{runtime_directory}/audio.wav")
    else:
        raise ValueError(f"File Scheme not yet implemented")

    logging_level = logging.ERROR
    if cli_args.verbose:
        logging_level = logging.DEBUG
    logging.basicConfig(
        level=logging_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    return Request(
        uri=cli_args.uri,
        id=id_value,
        langs=langs,
        paths=Paths(
            runtime_directory=runtime_directory,
            file_extension=file_extension,
            file_name=file_name,
            video_path=video_path,
            audio_path=audio_path
        ),
        verbose=cli_args.verbose,
        service_name=service_name,
        download=cli_args.download
    )


@app.command()
def info(uri: str = typer.Argument(..., help='URI (URL or file path)')):
    cli_args = CliArgs(uri=uri)
    request = build_request(cli_args)
    pprint(request)
    print("Local Transcripts:")
    list_transcripts(request)


def list_transcripts(request: Request):
    """
    :param request:
    :return: a list of local transcripts path
    """
    for item in request.paths.runtime_directory.iterdir():
        item: Path
        if not item.is_file():
            continue
        if not item.name.startswith('subtitle'):
            # not a subtitle
            continue
        # in a non-agent mode, we print all available subtitle file
        print(item)


def get_transcript_from_runtime_dir(request: Request):
    """
    :param request:
    :return: the local transcript path or empty if none was found
    """
    subtitle_path: Path | None = None
    for item in request.paths.runtime_directory.iterdir():
        item: Path
        if not item.is_file():
            continue
        if not item.name.startswith('subtitle'):
            # not a subtitle
            continue
        if not item.suffix.lower() == '.txt':
            continue
        if not request.langs is None:
            subtitle_language = Path(item.name).stem.split(".", 1)[1]
            asked_lang = request.langs[0]
            if not asked_lang in subtitle_language.lower():
                continue
        subtitle_path = item
        break
    return subtitle_path


def get_transcript_from_request(request: Request) -> Response:
    if request.service_name == "file":
        raise Exception("File processing is not yet implemented")

    # Check if we have it locally
    actual_transcript_path = get_transcript_from_runtime_dir(request)
    if actual_transcript_path:
        return Response(
            path=actual_transcript_path
        )

    # Download/Transcribe
    final_error = None
    try:
        # Download subtitle and optionally the video
        execute_yt_dlp(request)
    except SystemExit as e:
        # We capture it as the error could be after that the transcript as been downloaded
        # example: processing thumbnail: ERROR: Preprocessing: Error opening output files: Invalid argument
        final_error = e

    # Post processing (vtt file, transcribe)
    post_processing(request)

    return Response(
        path=get_transcript_from_runtime_dir(request),
        error=final_error
    )


@app.command()
def get(uri: str = typer.Argument(..., help='URI (URL or file path)'),
        langs: Optional[str] = typer.Option(None, '-l', '--langs', help='Language codes (e.g., es,fr)'),
        agent: bool = typer.Option(False, '-a', '--agent', help='Agent mode'),
        verbose: bool = typer.Option(False, '-v', '--verbose', help='Verbose mode'),
        download: bool = typer.Option(False, '-ds', '--download-source', help='Download the source video')
        ):
    """Transcribe audio/video from a URI"""

    cli_args = CliArgs(uri=uri, lang=langs, verbose=verbose, download=download)
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


@app.command(name="mcp")
def mcp_command(transport: McpTransport = typer.Option(McpTransport.stdio, help="Transport protocol")):
    logger.info(f"{transport.name} Mcp server started")
    mcp_run(transport)


if __name__ == '__main__':
    app()
