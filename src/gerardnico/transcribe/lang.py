import langcodes
from gerardnico.transcribe.api import TRANSCRIPT_PREFIX
from pathlib import Path

import logging

logger = logging.getLogger(__name__)

# orig is a lang suffix of YouTube
# it the video is in nl, you get 2 subtitles, `nl` and `nl-orig`
LANG_ORIGINE = "orig"

def normalize_transcript_path(path: Path) -> "Path":
    """
    Return a transcript path with a normalized lang
    ie transcript.subtitle.eng-US.vtt to transcript.subtitle.en.vtt
    """
    if path.is_dir():
        return path
    if not path.name.startswith(TRANSCRIPT_PREFIX):
        return path

    parts = path.name.split(".")
    if len(parts) < 3:
        return path

    locale_part = parts[-2]

    if locale_part == LANG_ORIGINE:
        return path

    try:
        lc = langcodes.Language.get(locale_part)
        lang = lc.language
    except langcodes.tag_parser.LanguageTagError:
        raise Exception(f"{path.name}: '{locale_part}' is not a valid locale tag value ")

    if lang is None:
        raise Exception(f"{path.name}: '{locale_part}' does not return any lang")

    if lang == locale_part:
        return path

    new_parts = parts[:-2] + [lang] + [parts[-1]]
    # noinspection PyTypeChecker
    new_name = ".".join(new_parts)
    return path.with_name(new_name)


def normalize_lang(lang: str | None):
    if lang is None:
        return None
    lc = langcodes.Language.get(lang)
    return lc.language
