import logging
import subprocess
from pathlib import Path

import torch
import whisper

from gerardnico.transcribe.api import Request, TRANSCRIPT_PREFIX

logger = logging.getLogger(__name__)


def get_whisper_output_path(request: Request, lang):
    """Return the transcript file path"""
    return Path(f"{request.runtime_directory}/{TRANSCRIPT_PREFIX}.whisper.{lang}.txt")


# Needs vc on Windows but download the model automatically
def transcribe_with_openai_whisper(request: Request, model_name: str = "base"):
    """
    Transcribe with open ai whisper
    :param request:
    :param model_name: see https://github.com/openai/whisper#available-models-and-languages
    """
    logger.debug(f"Loading model {model_name}")
    # https://github.com/openai/whisper#available-models-and-languages
    # base.en = 1 Gb Vram - doesn't have language tokens so it can't perform lang id

    # load audio and pad/trim it to fit 30 seconds
    logger.debug(f"Loading audio {request.audio_path}")
    chunk_number = 30
    CHUNK = chunk_number * whisper.audio.SAMPLE_RATE  # 30s chunks

    audio = whisper.load_audio(str(request.audio_path))
    chunks = [audio[i:i + CHUNK] for i in range(0, len(audio), CHUNK)]
    device = "cuda" if torch.cuda.is_available() else "cpu"

    # lang detection
    lang = "en" if model_name.endswith(".en") else request.lang
    model = whisper.load_model(model_name)
    if lang is None:
        logger.info(f"No lang requested, detecting language")
        mel = whisper.log_mel_spectrogram(chunks[0], n_mels=model.dims.n_mels).to(device)
        # noinspection PyArgumentList
        _, probs = model.detect_language(mel)
        lang = max(probs, key=probs.get)
        logger.info(f"Detected language: {lang}")
        if lang == "en" and not model_name.endswith(".en"):
            model = whisper.load_model(f"{model_name}.en")

    logger.info(f"Transcribe/decode the audio in {len(chunks)} chunks of {chunk_number} seconds")
    whisper_transcript_path = get_whisper_output_path(request, lang)
    with open(whisper_transcript_path, "w", encoding="utf-8") as f:
        for index, chunk in enumerate(chunks):
            logger.info(f"Chunk {index}")
            chunk = whisper.pad_or_trim(chunk)
            # make log-Mel spectrogram
            mel = whisper.log_mel_spectrogram(chunk, n_mels=model.dims.n_mels).to(device)
            # decoding
            options = whisper.DecodingOptions(language=lang, temperature=0.0, without_timestamps=False)
            result = whisper.decode(model, mel, options)
            if isinstance(result, list):
                transcript = " ".join(r.text for r in result)
            else:
                transcript = result.text
            logger.info(f"{transcript}")
            f.write(transcript)
            f.flush()
    logger.info(f"Transcript written at {whisper_transcript_path}")


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
