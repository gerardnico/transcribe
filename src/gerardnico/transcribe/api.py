import logging
import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse, ParseResult, parse_qs

from gerardnico.transcribe.error import AppError

logger = logging.getLogger(__name__)


# The mcp transport
class McpTransport(str, Enum):
    stdio = "stdio"
    http = "http"


@dataclass
class Service:
    home_directory: Path = None
    mcp_transport: McpTransport = McpTransport.stdio
    oauth2_client_id: str | None = None
    oauth2_client_secret: str | None = None
    # the external origin (ie 127.0.0.1:8000 or the dns name)
    oauth2_origin: str | None = None
    oauth2_authorized_emails: set[str] | None = None
    ssl_cert_file: Path | None = None
    ssl_key_file: Path | None = None
    # binding_host: should be 0.0.0.0 for external access
    binding_host: str = "127.0.0.1"
    binding_port: int = 8000


@dataclass
class Request:
    # The original uri
    uri: str
    lang: str | None
    runtime_directory: Path
    file_name: str
    file_extension: str
    video_path: Path
    # The resulting audio file path
    audio_path: Path
    # The id
    id: str
    # The service (File, YouTube, ...)
    service_name: str
    # download the file?
    download: bool
    # Verbose
    verbose: bool = False


@dataclass
class Context:
    service: Service
    request: Request | None = None


@dataclass
class Response:
    path: Path | None
    error: AppError | None = field(default=None)


# Not the localhost name because there is a DNS resolution
localhost = "127.0.0.1"


class ContextBuilder:
    verbose: bool = False
    uri: str = None
    home: str | None = None
    print_context: bool|None = None
    lang: Optional[str] = None
    # download the source file?
    download_source: bool = False
    # mcp Transport
    transport: McpTransport = McpTransport.stdio
    # host
    host: str = localhost
    port: int = 8000
    origin: str | None = None

    def __init__(self, verbose=False):
        self.verbose = verbose
        logging_level = logging.ERROR
        if verbose:
            logging_level = logging.DEBUG
        logging.basicConfig(
            level=logging_level,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        )
        logger.info(f"Logging level set to {logging_level}")

    def build(self) -> Context:
        """
        Build a request object from cli/tool arguments
        """

        # Determine the runtime directory (download for social url)
        # Note that if we want to add a timestamp, we
        # * need to get the info.json first
        # or, we can add `%(upload_date>%Y-%m-%d)s` in a template
        transcribe_home = self.home
        if not transcribe_home:
            transcribe_home = os.environ.get('TRANSCRIBE_HOME')
            if not transcribe_home:
                transcribe_home = os.environ.get('HOME') + "/.transcribe"

        ssl_key_file = None
        ssl_cert_file = None

        # Oauth
        client_id = os.environ.get("OAUTH_CLIENT_ID", "").strip()
        client_secret = os.environ.get("OAUTH_CLIENT_SECRET", "").strip()
        raw_emails = os.environ.get("AUTHORIZED_EMAILS", "").strip()
        authorized_emails = {
            email.strip().lower()
            for email in raw_emails.split(",")
            if email.strip()
        }

        # certificates for ssl
        # mandatory for local test because the server needs to be in ssl
        sslCertsDir = Path("./ssl-certs")
        expected_cert_path = Path(sslCertsDir, "cert.pem")
        if expected_cert_path.exists():
            ssl_cert_file = expected_cert_path
            expected_key_path = Path(sslCertsDir, "key.pem")
            if not expected_key_path.exists():
                raise ValueError(
                    f"When a cert exists, a key file should be available and was not found at {expected_key_path}")
            ssl_key_file = expected_key_path

        # origin for oauth
        origin = self.origin
        if not origin:
            # noinspection HttpUrlsUsage
            origin = f"http://{self.host}:{self.port}"

        service = Service(
            home_directory=Path(transcribe_home),
            oauth2_client_id=client_id,
            oauth2_client_secret=client_secret,
            oauth2_authorized_emails=authorized_emails,
            oauth2_origin=origin,
            mcp_transport=self.transport,
            ssl_cert_file=ssl_cert_file,
            ssl_key_file=ssl_key_file,
            binding_host=self.host,
            binding_port=self.port
        )

        # If we start the mcp server, there is no uri
        if not self.uri:
            return Context(
                service
            )

        parsed_uri: ParseResult = urlparse(self.uri)
        if not parsed_uri.scheme or parsed_uri.scheme == "file":
            service_name = "file"
        else:
            apex_name = parsed_uri.netloc  # authority

            # remove www. if present
            if apex_name.startswith("www."):
                apex_name = apex_name[4:]

            # service name is the first part before the dot
            service_name = apex_name.split('.')[0]

        # YouTube URL handling
        if service_name == "youtube":
            # YouTube video ID is usually in the 'v' query parameter
            query_params = parse_qs(parsed_uri.query)
            id_value = query_params.get('v', [''])[0]
        # TikTok URL handling
        elif service_name == "tiktok":
            # TikTok ID is made of username (without @) + last part of path
            path_parts = [p for p in parsed_uri.path.split('/') if p]
            if len(path_parts) != 3 or (not path_parts[0].startswith('@')) or path_parts[1] != 'video':
                raise ValueError("The tiktok url is not valid")
            username = path_parts[0][1:]  # remove @
            video_id = path_parts[2]
            id_value = f"{username}-{video_id}"
        elif service_name == "x" or service_name == "twitter":
            # https://x.com/forrestpknight/status/2012561898097594545
            path_parts = [p for p in parsed_uri.path.split('/') if p]
            if len(path_parts) != 3 and path_parts[1] != 'status':
                raise ValueError("The x url is not valid")
            username = path_parts[0]
            video_id = path_parts[2]
            id_value = f"{username}-{video_id}"
        elif service_name == "file":
            id_value = f'{parsed_uri.path}'
        else:
            raise ValueError(f"{service_name} not yet supported")

        runtime_directory = Path(f"{transcribe_home}/{service_name}/{id_value}")
        runtime_directory.mkdir(parents=True, exist_ok=True)

        # orig is a lang suffix of YouTube
        # it the video is in nl, you get 2 subtitles, `nl` and `nl-orig`
        orig = "orig"
        if self.lang is None:
            if service_name == "youtube":
                lang = orig
            else:
                # we let yt-dlp decide, normally the spoken language of the video
                lang = None
        else:
            lang = self.lang

        # Compute derived properties
        # file type
        if parsed_uri.scheme != 'file':
            # social media request
            file_extension = "mp4"
            file_name = f"video.{file_extension}"
            video_path = Path(f"{runtime_directory}/{file_name}")
            audio_path = Path(f"{runtime_directory}/audio.wav")
        else:
            raise ValueError(f"File Scheme not yet implemented")

        # download-source ?
        download_source = self.download_source
        if download_source and video_path.exists():
            download_source=False

        return Context(
            service,
            Request(
                uri=self.uri,
                id=id_value,
                lang=lang,
                runtime_directory=runtime_directory,
                file_extension=file_extension,
                file_name=file_name,
                video_path=video_path,
                audio_path=audio_path,
                service_name=service_name,
                download=download_source,
                verbose=self.verbose,
            )
        )

    def set_uri(self, param):
        self.uri = param
        return self

TRANSCRIPT_PREFIX = "transcript"
"""
Transcript prefix
# yt-dlp: {TRANSCRIPT_PREFIX}.subtitle.{lang}.%(ext)s",
# whisper: {TRANSCRIPT_PREFIX}.whisper.{lang}.txt",
"""