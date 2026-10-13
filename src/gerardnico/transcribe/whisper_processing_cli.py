from pathlib import Path

import logging
import subprocess

from gerardnico.transcribe.api import Request, TRANSCRIPT_PREFIX
logger = logging.getLogger(__name__)

def get_whisper_output_path(request: Request, lang):
    """Return the transcript file path"""
    return Path(f"{request.runtime_directory}/{TRANSCRIPT_PREFIX}.whisper.{lang}.txt")


# Need more setup. Does not download the model for instance and needs to be compiled
# deprecated
def transcribe_with_gcc_whisper(request: Request):
    output_format_whisper_argument = "--output-txt"

    # https://github.com/ggml-org/whisper.cpp/tree/master/examples/cli
    # --print-colors

    whisper_model_name = "base"
    lang = "en" if request.lang is None else request.lang
    if lang == "en":
        # The .en models (tiny.en, base.en, small.en, medium.en) are English-only and will always translate to English
        whisper_model_name = "base.en"
    output_file_path = get_whisper_output_path(request, lang)
    if Path(output_file_path).exists():
        logger.debug(f"Transcribed output Speech file already exists: {output_file_path}")
        return
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
        "--output-file", str(output_file_path).replace(".txt", ""),  # without the extension
        output_format_whisper_argument,
        "-f", request.audio_path
    ]

    try:
        subprocess.run(command)
        logger.info("Audio Speech to text transformation was successful")
    except subprocess.CalledProcessError as e:
        logger.error(f"Error occurred: {e}")
        logger.error(f"Error output: {e.stderr}")
