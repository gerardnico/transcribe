from gerardnico.transcribe import lang

from pathlib import Path

from gerardnico.transcribe.api import TRANSCRIPT_PREFIX


def test_normalize_transcript_file():
    input_path = Path(f"{TRANSCRIPT_PREFIX}.subtitle.eng-US.vtt")
    path =  lang.normalize_transcript_path(input_path)
    assert path.name == f"{TRANSCRIPT_PREFIX}.subtitle.en.vtt"
