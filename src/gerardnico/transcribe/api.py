import logging
import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional, List
from urllib.parse import urlparse, ParseResult, parse_qs

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
    oauth2_authorized_emails: set[str] | None = None
    ssl_cert_file: Path | None = None
    ssl_key_file: Path | None = None


@dataclass
class Request:
    # The original uri
    uri: str
    langs: Optional[List[str]] | None
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
    error: SystemExit | None = field(default=None)


class ContextBuilder:
    verbose: bool = False
    uri: str = None
    home: str | None = None
    lang: Optional[str] = None
    # download the source file?
    downloadSource: bool = False
    # mcp Transport
    transport: McpTransport = McpTransport.stdio

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

        client_id = None
        authorized_emails = None
        ssl_keyfile = None
        ssl_cert_file = None
        if self.transport == McpTransport.http:
            client_id = os.environ.get("GOOGLE_CLIENT_ID", "").strip()
            if not client_id:
                raise ValueError("GOOGLE_CLIENT_ID must be set for HTTP transport")

            raw_emails = os.environ.get("AUTHORIZED_EMAILS", "").strip()
            if not raw_emails:
                raise ValueError("AUTHORIZED_EMAILS must be set for HTTP transport")

            authorized_emails = {
                email.strip().lower()
                for email in raw_emails.split(",")
                if email.strip()
            }
            if not authorized_emails:
                raise ValueError("AUTHORIZED_EMAILS must contain at least one email address")

            # certificates
            # mandatory for local test because the server needs to be in ssl
            sslCertsDir = Path("./ssl-certs")
            expected_cert_path = Path(sslCertsDir, "cert.pem")
            if expected_cert_path.exists():
                ssl_cert_file = expected_cert_path
                expected_key_path = Path(sslCertsDir, "key.pem")
                if not expected_key_path.exists():
                    raise ValueError(
                        f"When a cert exists, a key file should be available and was not found at {expected_key_path}")

        service = Service(
            home_directory=Path(transcribe_home),
            oauth2_client_id=client_id,
            oauth2_authorized_emails=authorized_emails,
            ssl_cert_file=ssl_cert_file,
            ssl_key_file=ssl_keyfile
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

        # orig is a lang suffix of YouTube
        # it the video is in nl, you get 2 subtitles, `nl` and `nl-orig`
        orig = "orig"
        if self.lang is None:
            if service_name == "youtube":
                langs = [orig]
            else:
                # we let yt-dlp decide, normally the spoken language of the video
                langs = None
        else:
            langs = self.lang.split(",")

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

        return Context(
            service,
            Request(
                uri=self.uri,
                id=id_value,
                langs=langs,
                runtime_directory=runtime_directory,
                file_extension=file_extension,
                file_name=file_name,
                video_path=video_path,
                audio_path=audio_path,
                service_name=service_name,
                download=self.downloadSource,
                verbose=self.verbose,
            )
        )

    def set_uri(self, param):
        self.uri = param
        return self
