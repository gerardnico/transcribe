import logging
from pathlib import Path

from gerardnico.transcribe.api import Response, Request
from gerardnico.transcribe.error import AppError
from gerardnico.transcribe.ffmpeg import video_to_audio
from gerardnico.transcribe.social import execute_yt_dlp
from gerardnico.transcribe.vtt import post_processing_vtt
from gerardnico.transcribe.whisper import post_processing_transcribe_audio_to_text

logger = logging.getLogger(__name__)


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
    except AppError as e:
        # We capture it as the error could be after that the transcript as been downloaded
        # example: processing thumbnail: ERROR: Preprocessing: Error opening output files: Invalid argument
        final_error = e

    # Post processing (vtt file, transcribe)
    post_processing(request)

    return Response(
        path=get_transcript_from_runtime_dir(request),
        error=final_error
    )


def get_transcript_from_runtime_dir(request: Request):
    """
    :param request: the request data
    :return: the local transcript path or empty if none was found
    """
    subtitle_path: Path | None = None
    for item in request.runtime_directory.iterdir():
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


def list_transcripts(request: Request):
    """
    :param request:
    :return: a list of local transcripts path
    """
    directory = request.runtime_directory
    if not directory.exists():
        print("No transcript found")
        return
    for item in directory.iterdir():
        item: Path
        if not item.is_file():
            continue
        if not item.name.startswith('subtitle'):
            # not a subtitle
            continue
        # print all available subtitle file
        print(item)


def post_processing(request: Request) -> None:
    """
    Scan all files in a directory
    * extract clean text, and save as .txt files.
    * transcribe if needed

    Args:
        request: The context object
    """
    directory_path = request.runtime_directory

    if not directory_path.exists():
        raise ValueError(f"Runtime Directory does not exist: {directory_path}")

    vtt_file_count = 0
    for item in directory_path.iterdir():
        # Check if it's a file and has .vtt extension
        if item.is_file() and item.suffix.lower() == '.vtt':
            post_processing_vtt(item)
            vtt_file_count += 1

    if vtt_file_count == 0:
        logger.info(f"No .vtt files found in {directory_path}")
    else:
        logger.info(f"Processed {vtt_file_count} VTT file(s)")

    logger.info(f"Trying to transcribe")
    if get_speech_to_text(request, vtt_file_count):
        video_to_audio(request)
        post_processing_transcribe_audio_to_text(request)


def get_speech_to_text(request: Request, vtt_file_count):
    if not vtt_file_count == 0:
        logger.debug(f"  * Subtitle file found, no speech to text needed")
        return False
    if not Path(request.video_path).exists():
        logger.debug(f"  * Video is not present, no transcription")
        return False
    return True


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
