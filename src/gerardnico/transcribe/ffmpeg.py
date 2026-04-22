import subprocess
from pathlib import Path

from gerardnico.transcribe.api import Context
import logging
logger = logging.getLogger(__name__)

def video_to_audio(request: Context):

    if Path(request.paths.audio_path).exists():
        logger.debug(f"Audio file already exist: {request.paths.audio_path}")
        return

    command = [
        "ffmpeg",
        "-i", f"{request.paths.video_path}",
        "-ar", "16000",
        "-ac", "1",
        "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
        "-c:a", "pcm_s16le",
        request.paths.audio_path
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
