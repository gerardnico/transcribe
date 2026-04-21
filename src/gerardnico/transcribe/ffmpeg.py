import subprocess
from pathlib import Path

from src.gerardnico.transcribe.cli import logger


def video_to_audio(context):
    if context.mode.type == 'audio':
        raise ValueError("Audio processing not yet implemented")

    if Path(context.mode.audio_path).exists():
        logger.debug(f"Audio file already exist: {context.mode.audio_path}")
        return

    command = [
        "ffmpeg",
        "-i", f"{context.mode.video_path}",
        "-ar", "16000",
        "-ac", "1",
        "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
        "-c:a", "pcm_s16le",
        context.mode.audio_path
    ]

    try:
        result = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True
        )
        logger.info("Video to audio transformation was successful")
        logger.info(result.stdout)
    except subprocess.CalledProcessError as e:
        logger.error(f"Error occurred: {e}")
        logger.error(f"Error output: {e.stderr}")
