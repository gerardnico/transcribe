import logging

from gerardnico.transcribe.api import Request, TRANSCRIPT_PREFIX
from gerardnico.transcribe.whisper_processing_cli import get_whisper_output_path

logger = logging.getLogger(__name__)

import torch
import whisper


# Needs vc on Windows but download the model automatically
def transcribe_with_openai_whisper(request: Request, model_name: str = "base"):
    """
    Transcribe with the open ai whisper library
    :param request:
    :param model_name: see https://github.com/openai/whisper#available-models-and-languages
    """
    logger.debug(f"Loading model {model_name}")
    # https://github.com/openai/whisper#available-models-and-languages
    # base.en = 1 Gb Vram - doesn't have language tokens so it can't perform lang id

    # load audio and pad/trim it to fit 30 seconds
    logger.debug(f"Loading audio {request.audio_path}")
    chunk_number = 30
    chunk = chunk_number * whisper.audio.SAMPLE_RATE  # 30s chunks

    audio = whisper.load_audio(str(request.audio_path))
    chunks = [audio[i:i + chunk] for i in range(0, len(audio), chunk)]
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
