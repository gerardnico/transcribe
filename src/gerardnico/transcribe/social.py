import contextlib
import io
import logging
import os
from pathlib import Path

import yt_dlp
from gerardnico.transcribe.api import Request, TRANSCRIPT_PREFIX, Provider
from gerardnico.transcribe.error import AppError

logger = logging.getLogger(__name__)


def get_cookie_file(request: Request):
    """Return a session cookie file from the service name and session id"""
    cookie_file = (
        Path(request.runtime_directory)
        / f"cookies-{request.session_id}.txt"
    )
    if cookie_file.exists():
        return str(cookie_file)

    cookie_file.parent.mkdir(parents=True, exist_ok=True)

    cookie_template = (request.resource_directory / "cookies" / f"{request.provider}.txt")

    if not cookie_template.exists():
        raise AppError(
            f"Cookie template file does not exist for service '{request.provider}': {cookie_template}",
            1,
        )

    template_content = cookie_template.read_text(encoding="utf-8")
    assert request.session_id is not None
    session_cookie_content = template_content.replace(
        "%%session_id_placeholder%%", request.session_id
    )
    cookie_file.write_text(session_cookie_content, encoding="utf-8")

    return str(cookie_file)


def execute_yt_dlp(request: Request, session_id: str | None = None):
    """
    Execute the yt-dlp command
    Raises:
        AppError: If execution exits
    """
    args = []

    # Download video?
    if request.download:
        args += [
            # https://github.com/yt-dlp/yt-dlp#preset-aliases
            "-t", request.file_extension,
            # indicate a template for the output file names
            # https://github.com/yt-dlp/yt-dlp#output-template
            "-o", request.file_name
        ]
    else:
        args += [
            # Do not download the video but write all related files (Alias: --no-download)
            "--skip-download"
        ]

    # Subtitle Lang determination
    # Split by comma and loop
    langs_regexp = []
    case_insensitivity_flag = "(?i)"
    lang_separator = ','
    found_orig = False
    orig = "orig"

    # YouTube block by video once you are blocked, it can take time,
    # but it will work with another video
    sleep = len(langs_regexp) * 2

    # We use the main cli
    # because it's also possible to embed it, but it's a pain in the ass
    # the options are not the same as the doc and the download happens as an option
    # For embedding, see https://github.com/yt-dlp/yt-dlp?tab=readme-ov-file#embedding-yt-dlp
    #
    # To get video info, it's:
    # with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    #    info = ydl.extract_info(url, download=False)

    # Lang selections:
    # By default, we don't set a lang. We let yt-dlp decide
    # --sub-langs: Languages of the subtitles to download (can be regex) or "all" separated by commas, e.g.
    # --sub-langs "en.*,ja" (where "en.*" is a regex pattern that matches "en" followed by 0 or more of any character).
    # You can prefix the language code with a "-" to exclude it from the requested languages, e.g.
    # --sub-langs all,-live_chat. Use --list-subs for a list of available language tags
    if not request.lang is None:
        if request.lang == orig:
            found_orig = True
            langs_regexp.append(f"{case_insensitivity_flag}.*-{orig}.*")
        else:
            langs_regexp.append(f"{case_insensitivity_flag}{request.lang}.*")
        langs_ytd = lang_separator.join(langs_regexp)
        # Don't download the orig subtitle if not specified
        if found_orig == False and request.provider == "youtube":
            langs_ytd = f"{langs_ytd}{lang_separator}-.*-{orig}.*"
        args += [
            "--sub-langs",
            f"{langs_ytd}"
        ]

    # session id is given only when an auth is needed
    session_id = session_id
    if not session_id:
        session_id = request.session_id
    if session_id:
        args += [
            # mandatory when the content is flagged, or we get a 403
            "--cookies", get_cookie_file(request),
        ]

    args += [
        # Download the subtitle (not generated)
        "--write-subs",
        # Write automatically generated subtitle file (Alias: --write-automatic-subs)
        "--write-auto-subs",
        # Subtitle format; accepts formats preference separated by "/", e.g. "srt" or "ass/srt/best"
        "--sub-format", "vtt/srt/best",
        # For the output file names, this is a template string
        # https://github.com/yt-dlp/yt-dlp#output-template
        # "-o", "subtitle:%(extractor)s-%(uploader)s-%(id)s.%(ext)s",
        "-o", f"subtitle:{TRANSCRIPT_PREFIX}.subtitle.%(ext)s",
        # Write video metadata to a .info.json file
        "--write-info-json",
        "-o", f"infojson:data",  # file is data.info.json
        # Location in the filesystem where yt-dlp can store some downloaded information (such as
        # client ids and signatures) permanently. By default, ${XDG_CACHE_HOME}/yt-dlp
        # --cache-dir DIR
        # Write thumbnail image to disk (extension is image when unknown - mostly webp)
        # originCover
        "--write-thumbnail",
        # not .%(ext)s as it's added by yt_dlp as image
        "-o", f"thumbnail:thumbnail",
        # Number of seconds to sleep before each subtitle download
        "--sleep-subtitles", f"{sleep}",
        # The paths where the files should be downloaded.
        # Specify the type of file and the path separated by a colon ":". All the same
        # TYPES as --output are supported. Additionally, you can also provide "home" (default) and "temp" paths.
        # All intermediary files are first downloaded to the temp path and then the final files are moved over to
        # the home path after download is finished.
        # This option is ignored if --output is an absolute path
        # Specify the working directory (home)
        "--paths", f"home:{request.runtime_directory}",
        # put all temporary files in "wd\tmp"
        "--paths", "temp:tmp",
        # put all subtitle files in home/working directory
        "--paths", "subtitle:.",
        request.uri
    ]

    if request.provider != Provider.TIKTOK:
        # Does not work on TikTok: bug on yt-dlp as the extension is given by the last name in the path
        # and not by the content type return type
        # So we get a file-origin.image with this  URL example: https://tiktokcdn-eu.com/file-origin.image?dr=10395&x-expires
        #
        # Convert the thumbnails to another format (currently supported: jpg, png, webp)
        args += [
            "--convert-thumbnails", "webp",
        ]

    yt_dlp_command = "yt-dlp " + " ".join(f"\"{str(x)}\"" for x in args)
    logger.info(f"Command: {yt_dlp_command}")

    # execution and stdout/stderr capture
    stdout_buf = io.StringIO()
    stderr_buf = io.StringIO()
    final_system_exit: SystemExit | None = None
    with contextlib.redirect_stdout(stdout_buf), contextlib.redirect_stderr(stderr_buf):
        try:
            yt_dlp.main(args)
        except SystemExit as e:
            # yt_dlp.main(args) finish with a SystemExit every time even on success
            final_system_exit = e

    # we create another error with the stdout for more context
    std = stdout_buf.getvalue() + stderr_buf.getvalue()
    if request.verbose:
        # history, we don't use the --quiet and --no-warnings
        # because an error in yt-dlp without context has no value
        # example:
        # the error: ERROR: Preprocessing: Error opening output files: Encoder not found
        # can not be understood without the stdout: [ThumbnailsConvertor] Converting thumbnail .image to webp
        if not request.verbose:
            args += [

            ]
        logger.info(f"yt-dlp stdout and stderr:\n{std}")

    # Note that if there is any error, the transcript may have been downloaded
    # example: processing thumbnail: ERROR: Preprocessing: Error opening output files: Invalid argument
    if final_system_exit is not None and final_system_exit.code != 0:

        # 403 and request without session id
        if session_id is None and (std.__contains__("403") or std.__contains__("Log in for access")):
            if request.provider == "tiktok":
                tiktok_session_id = os.environ.get("TIKTOK_SESSION_ID", None)
                if tiktok_session_id:
                    execute_yt_dlp(request, tiktok_session_id)
            return
        raise AppError(
            f"Yt_dlp download error has occurred. Stderr was: {std}\nwith command: {yt_dlp_command}",
            0 if final_system_exit.code is None else final_system_exit.code) \
            from final_system_exit
