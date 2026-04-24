import contextlib
import io
import logging

import yt_dlp

from gerardnico.transcribe.api import Request, TRANSCRIPT_PREFIX
from gerardnico.transcribe.error import AppError

logger = logging.getLogger(__name__)


def execute_yt_dlp(request: Request):
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

    if not request.verbose:
        args += [
            "--quiet",
            "--no-warnings"
        ]

    # Lang selections:
    # By default, we don't set a lang. We let yt-dlp decide
    # --sub-langs: Languages of the subtitles to download (can be regex) or "all" separated by commas, e.g.
    # --sub-langs "en.*,ja" (where "en.*" is a regex pattern that matches "en" followed by 0 or more of any character).
    # You can prefix the language code with a "-" to exclude it from the requested languages, e.g.
    # --sub-langs all,-live_chat. Use --list-subs for a list of available language tags
    if not request.lang is None:
        for lang in request.lang:
            if lang == orig:
                found_orig = True
                langs_regexp.append(f"{case_insensitivity_flag}.*-{orig}.*")
            else:
                langs_regexp.append(f"{case_insensitivity_flag}{lang}.*")
        langs_ytd = lang_separator.join(langs_regexp)
        # Don't download the orig subtitle if not specified
        if found_orig == False and request.service_name == "youtube":
            langs_ytd = f"{langs_ytd}{lang_separator}-.*-{orig}.*"
        args += [
            "--sub-langs",
            f"{langs_ytd}"
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
        # Convert the thumbnails to another format (currently supported: jpg, png, webp)
        "--convert-thumbnails", "webp",
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
    logger.info("Command: yt-dlp " + " ".join(str(x) for x in args))

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

    # Note that if there is any error, the transcript may have been downloaded
    # example: processing thumbnail: ERROR: Preprocessing: Error opening output files: Invalid argument
    if final_system_exit is not None and final_system_exit.code != 0:
        # we create another error with the stdout for more context
        raise AppError(f"Transcript download error has occurred: {stdout_buf.getvalue()} {stderr_buf.getvalue()}",
                      0 if final_system_exit.code is None else final_system_exit.code) from final_system_exit
