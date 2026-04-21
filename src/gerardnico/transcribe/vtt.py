import logging
from pathlib import Path

import webvtt

logger = logging.getLogger(__name__)


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
