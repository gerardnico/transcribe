from gerardnico.transcribe.api import McpTransport, localhost, Context, Service, Request
from typing import Optional
import os
from pathlib import Path
import logging

from gerardnico.transcribe.lang import LANG_ORIGINE

logger = logging.getLogger(__name__)
from urllib.parse import urlparse, ParseResult, parse_qs
import gerardnico.transcribe.lang as lang_package


def context_builder(
    verbose: bool = False,
    uri: str | None = None,
    home: str | None = None,
    lang: Optional[str] = None,
    # download the source file?
    download_source: bool = False,
    # mcp Transport
    transport: McpTransport = McpTransport.stdio,
    # host
    host: str = localhost,
    # port: not 8000 because it's too common and will clash with already started process (such as kubelogin for instance)
    port: int = 8206,
    origin: str | None = None,
    session_id: str | None = None
):
    verbose = verbose
    logging_level = logging.INFO
    if verbose:
        logging_level = logging.DEBUG
    logging.basicConfig(
        level=logging_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    logger.info(f"Logging level set to {logging_level}")

    """
    Build a request object from cli/tool arguments
    """

    # Determine the runtime directory (download for social url)
    # Note that if we want to add a timestamp, we
    # * need to get the info.json first
    # or, we can add `%(upload_date>%Y-%m-%d)s` in a template
    transcribe_home = home
    if not transcribe_home:
        transcribe_home = os.environ.get('TRANSCRIBE_HOME')
        if not transcribe_home:
            transcribe_home = os.environ.get('HOME') + "/.transcribe"

    ssl_key_file = None
    ssl_cert_file = None

    # Oauth
    client_id = os.environ.get("OAUTH_CLIENT_ID", "").strip()
    client_secret = os.environ.get("OAUTH_CLIENT_SECRET", "").strip()
    # origin for oauth
    origin = origin
    if not origin:
        origin = os.environ.get("OAUTH_ORIGIN", "").strip()
        if not origin:
            if host == "0.0.0.0":  # docker run
                # Mcp do not allow a non-local origin without https
                # ie this url is not allowed: http://0.0.0.0:8206
                origin = f"http://127.0.0.1:{port}"
            else:
                # noinspection HttpUrlsUsage
                origin = f"http://{host}:{port}"
    raw_emails = os.environ.get("AUTHORIZED_EMAILS", "").strip()
    authorized_emails = {
        email.strip().lower()
        for email in raw_emails.split(",")
        if email.strip()
    }
    # resources directory
    project_root = Path(__file__).resolve().parents[3]
    resources_directory = (project_root / "resources")

    # certificates for ssl
    # mandatory for local test because the server needs to be in ssl
    ssl_certs_dir = Path(resources_directory, "ssl-certs")
    expected_cert_path = Path(ssl_certs_dir, "cert.pem")
    if expected_cert_path.exists():
        ssl_cert_file = expected_cert_path
        expected_key_path = Path(ssl_certs_dir, "key.pem")
        if not expected_key_path.exists():
            raise ValueError(
                f"When a cert exists, a key file should be available and was not found at {expected_key_path}")
        ssl_key_file = expected_key_path

    service = Service(
        home_directory=Path(transcribe_home),
        oauth2_client_id=client_id,
        oauth2_client_secret=client_secret,
        oauth2_authorized_emails=authorized_emails,
        oauth2_origin=origin,
        mcp_transport=transport,
        ssl_cert_file=ssl_cert_file,
        ssl_key_file=ssl_key_file,
        binding_host=host,
        binding_port=port
    )

    # If we start the mcp server, there is no uri
    if not uri:
        return Context(
            service
        )

    parsed_uri: ParseResult = urlparse(uri)
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


    if lang is None:
        if service_name == "youtube":
            lang = LANG_ORIGINE
        else:
            # we let yt-dlp decide, normally the spoken language of the video
            lang = None
    else:
        lang = lang_package.normalize_lang(lang)

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
    download_source = download_source
    if download_source and video_path.exists():
        download_source = False

    return Context(
        service,
        Request(
            uri=uri,
            id=id_value,
            lang=lang,
            runtime_directory=runtime_directory,
            resource_directory=resources_directory,
            file_extension=file_extension,
            file_name=file_name,
            video_path=video_path,
            audio_path=audio_path,
            service_name=service_name,
            download=download_source,
            verbose=verbose,
            session_id=session_id
        )
    )
