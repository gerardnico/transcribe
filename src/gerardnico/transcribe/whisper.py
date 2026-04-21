import subprocess
from pathlib import Path

import logging
logger = logging.getLogger(__name__)


def post_processing_transcribe_audio_to_text(context):
    output_file_path_without_extension = f"{context.runtime_directory}/speech"
    output_format_extension = "txt"
    output_format_whisper_argument = "--output-txt"
    output_file_path = f"{output_file_path_without_extension}.{output_format_extension}"
    if Path(output_file_path).exists():
        logger.debug(f"Transcribed output Speech file already exists: {output_file_path}")
        return

    # https://github.com/ggml-org/whisper.cpp/tree/master/examples/cli
    # --print-colors

    whisper_model_name = "base"
    lang = context.lang[0]
    if lang == "en":
        # The .en models (tiny.en, base.en, small.en, medium.en) are English-only and will always translate to English
        whisper_model_name = "base.en"

    # Get the brew prefix for whisper-cpp
    brew_prefix = subprocess.check_output(
        ["brew", "--prefix", "whisper-cpp"],
        text=True
    ).strip()

    whisper_model = f"{brew_prefix}/models/ggml-{whisper_model_name}.bin"
    command = [
        "whisper-cli",
        "--model", whisper_model,
        "--no-timestamps",  # no timestamp left to the text
        # "--print-colors",  # confidence  - highlight words with high or low confidence:
        "--processors", "4",  # number of processors to use during computation
        "--language", lang,  # language
        "--output-file", output_file_path_without_extension,  # without the extension
        output_format_whisper_argument,
        "-f", context.paths.audio_path
    ]

    try:
        subprocess.run(command)
        logger.info("Audio Speech to text transformation was successful")
    except subprocess.CalledProcessError as e:
        logger.error(f"Error occurred: {e}")
        logger.error(f"Error output: {e.stderr}")
