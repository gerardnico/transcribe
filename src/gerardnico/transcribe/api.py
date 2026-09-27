import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from gerardnico.transcribe.error import AppError

logger = logging.getLogger(__name__)


# The mcp transport
class McpTransport(str, Enum):
    stdio = "stdio"
    http = "http"


@dataclass
class CliGlobalOptions:
    # Global options in the cli
    home_directory: Path | None
    print_context: bool | None
    verbose: bool | None


@dataclass
class Service:
    home_directory: Path = None
    mcp_transport: McpTransport = McpTransport.stdio
    oauth2_client_id: str | None = None
    oauth2_client_secret: str | None = None
    # the external origin (ie 127.0.0.1:8206 or the dns name)
    oauth2_origin: str | None = None
    oauth2_authorized_emails: set[str] | None = None
    ssl_cert_file: Path | None = None
    ssl_key_file: Path | None = None
    # binding_host: should be 0.0.0.0 for external access
    binding_host: str = "127.0.0.1"
    # 8206 (not 8000, too common)
    binding_port: int = 8206

class Provider(str, Enum):
    """The provider that we wrap"""
    TIKTOK = ("tiktok", "tiktok.com")
    YOUTUBE = ("youtube", "youtube.com")
    TWITTER = ("twitter", "x.com")
    FILE = ("other", None)

    def __new__(cls, value: str, host: str | None):
        # noinspection PyTypeChecker
        obj = str.__new__(cls, value)
        # https://docs.python.org/3/library/enum.html#supported-sunder-names
        obj._value_ = value
        # used to see if the agent makes calls to its base
        obj.host = host
        return obj

@dataclass
class Request:
    # The original uri
    uri: str
    lang: str | None
    runtime_directory: Path
    # where the resources are stored
    resource_directory: Path
    file_name: str
    file_extension: str
    video_path: Path
    # The resulting audio file path
    audio_path: Path
    # The id
    id: str
    # The provider name (File, YouTube, ...)
    provider: Provider
    # download the file?
    download: bool
    # Verbose
    verbose: bool = False
    # session id
    # some content are tagged as being not all public
    # and asked for a login, we need then to pass a session_id cookie
    # Example of video: https://www.tiktok.com/@frdric422/video/7613409335158279446
    # that would return: This post may not be comfortable for some audiences. Log in for access.
    session_id: str | None = None


@dataclass
class Context:
    # the context for the mcp service
    service: Service
    # the context when executing
    request: Request | None = None


@dataclass
class Response:
    path: Path | None
    error: AppError | None = field(default=None)


# Not the localhost name because there is a DNS resolution
localhost = "127.0.0.1"

TRANSCRIPT_PREFIX = "transcript"
"""
Transcript prefix
# yt-dlp: {TRANSCRIPT_PREFIX}.subtitle.{lang}.%(ext)s",
# whisper: {TRANSCRIPT_PREFIX}.whisper.{lang}.txt",
"""
