#!/usr/bin/env python3
"""
TikTok Transcript Downloader using yt-dlp
Downloads and formats transcripts from TikTok videos
"""
import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List
from urllib.parse import ParseResult
import logging
import webvtt

from src.gerardnico.transcribe.ffmpeg import video_to_audio
from src.gerardnico.transcribe.social import execute_yt_dlp
from src.gerardnico.transcribe.whisper import post_processing_transcribe_audio_to_text

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

# Info extract from the uru
@dataclass
class UriInfo:
    # The url apex name
    apex_name: str
    # The service (YouTube, ...)
    service_name: str
    # The id
    id: str
    # The parsed result
    uri: ParseResult


@dataclass
class ModeInfo:
    type: str
    file_name: Optional[str] = None
    file_extension: Optional[str] = None
    video_path: Optional[str] = None
    # The resulting audio file path
    audio_path: Optional[str] = None


@dataclass
class Context:
    video: UriInfo
    langs: List[str]
    runtime_directory: str
    mode: ModeInfo
    verbose: bool


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
    if context.mode.type != "video":
        logger.debug(f"  * Not a video mode, no transcription")
        return False
    if not Path(context.mode.video_path).exists():
        logger.debug(f"  * Video is not present, no transcription")
        return False
    return True


def post_processing(context: Context) -> None:
    """
    Scan all files in a directory
    * extract clean text, and save as .txt files.
    * transcribe if needed

    Args:
        context: The context object
    """
    directory = context.runtime_directory
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
    if get_transcription(context, vtt_file_count):
        video_to_audio(context)
        post_processing_transcribe_audio_to_text(context)


def parse_uri(uri) -> UriInfo:
    parsed_uri: ParseResult = urlparse(uri)
    apex_name = parsed_uri.netloc # authority

    # remove www. if present
    if apex_name.startswith("www."):
        apex_name = apex_name[4:]

    # service name is the first part before the dot
    service_name = apex_name.split('.')[0]

    # default id is empty
    id_value = ""

    # YouTube URL handling
    if "youtube.com" in apex_name:
        # YouTube video ID is usually in the 'v' query parameter
        query_params = parse_qs(parsed_uri.query)
        id_value = query_params.get('v', [''])[0]

    # TikTok URL handling
    elif "tiktok.com" in apex_name:
        # TikTok ID is made of username (without @) + last part of path
        path_parts = [p for p in parsed_uri.path.split('/') if p]
        if len(path_parts) != 3 or (not path_parts[0].startswith('@')) or path_parts[1] != 'video':
            raise ValueError("The tiktok url is not valid")
        username = path_parts[0][1:]  # remove @
        video_id = path_parts[2]
        id_value = f"{username}-{video_id}"
    elif "x.com" in apex_name:
        # https://x.com/forrestpknight/status/2012561898097594545
        path_parts = [p for p in parsed_uri.path.split('/') if p]
        if len(path_parts) != 3 and path_parts[1] != 'status':
            raise ValueError("The x url is not valid")
        username = path_parts[0]
        video_id = path_parts[2]
        id_value = f"{username}-{video_id}"

    return UriInfo(
        apex_name=apex_name,
        service_name=service_name,
        id=id_value,
        uri=parsed_uri
    )


def main():
    parser = ArgumentParserNoUsage(description='Get video transcripts')
    parser.add_argument('url', help='URI (Url or file path)')
    parser.add_argument('--langs', '-l',
                        help='The languages codes separated by a comma. Example for Spanish and French: es,fr'
                        )
    parser.add_argument('--mode', '-m',
                        default='text',
                        choices=['text', 'audio', 'video'],
                        help='The mode of execution: text (download the text subtitle file only) or video (download the video and transcribe)'
                        )
    parser.add_argument('--agent', '-a', action='store_true',
                        help='If this is an agent, the transcript is given textually to stdout'
                        )
    parser.add_argument('--verbose', '-v',
                        action='store_true',
                        help='Verbose mode'
                        )

    args = parser.parse_args()

    logging_level = logging.ERROR
    if args.verbose:
        logging_level = logging.DEBUG
    logging.basicConfig(
        level=logging_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    uri = args.url

    uri_info = parse_uri(uri)

    # Determine the runtime directory (download for social url)
    # Note that if we want to add a timestamp, we
    # * need to get the info.json first
    # or, we can add `%(upload_date>%Y-%m-%d)s` in a template
    runtime_directory = f"out/{uri_info.service_name}/{uri_info.id}"

    # orig is a lang suffix of YouTube
    # it the video is in nl, you get 2 subtitles, `nl` and `nl-orig`
    orig = "orig"
    if args.langs is None:
        if uri_info.service_name == "youtube":
            langs = [orig]
        else:
            # we let yt-dlp decide, normally the spoken language of the video
            langs = None
    else:
        langs = args.langs.split(",")

    # context building
    context = Context(
        video=uri_info,
        langs=langs,
        runtime_directory=runtime_directory,
        mode=ModeInfo(type=args.mode),
        verbose=args.verbose
    )

    # Compute derived properties
    # file type
    if context.mode.type == 'video':
        context.mode.file_extension = "mp4"
        context.mode.file_name = f"{context.mode.type}.{context.mode.file_extension}"
        context.mode.video_path = f"{context.runtime_directory}/{context.mode.file_name}"
        context.mode.audio_path = f"{context.runtime_directory}/audio.wav"
    elif context.mode.type == 'audio':
        context.mode.file_extension = "mp3"
        context.mode.file_name = f"{context.mode.type}.{context.mode.file_extension}"
        context.mode.audio_path = f"{context.runtime_directory}/{context.mode.file_name}"
        raise ValueError(f"{context.mode.type} not yet implemented")

    final_error = None
    try:
        # Download subtitle and optionally the video
        execute_yt_dlp(context)
    except SystemExit as e:
        # We capture it as the error could be after that the transcript as been downloaded
        # example: processing thumbnail: ERROR: Preprocessing: Error opening output files: Invalid argument
        final_error = e

    # Post processing (vtt file, transcribe)
    post_processing(context)

    # Result
    is_agent: bool = args.agent
    if is_agent:
        print(f"The transcript is:\n")
    else:
        print(f"Transcript files:")
    for item in Path(context.runtime_directory).iterdir():
        item: Path
        if not item.is_file():
            continue
        if not item.name.startswith('subtitle'):
            # not a subtitle
            continue
        if not is_agent:
            # in a non-agent mode, we print all available subtitle file
            print(item)
            continue
        # agent mode
        # output only the asked language in text mode
        if not item.suffix.lower() == '.txt':
            continue
        if not langs is None:
            subtitle_language = Path(item.name).stem.split(".", 1)[1]
            asked_lang = langs[0]
            if not asked_lang in subtitle_language.lower():
                continue
        print(item.read_text(encoding="utf-8"))
        break

    # Raise if any error
    if final_error is not None and final_error.code != 0:
        raise final_error


if __name__ == '__main__':
    main()
