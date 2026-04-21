from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional, List

@dataclass
class Paths:
    runtime_directory: Path
    file_name: str = None
    file_extension: str = None
    video_path: Path = None
    # The resulting audio file path
    audio_path: Path = None


@dataclass
class Request:
    # The original uri
    uri: str
    langs: Optional[List[str]] | None
    paths: Paths
    verbose: bool
    # The id
    id: str
    # The service (File, YouTube, ...)
    service_name: str
    # download the file?
    download: bool


@dataclass
class Response:
    path: Path | None
    error: SystemExit  | None = field(default=None)

# The mcp transport
class McpTransport(str, Enum):
    stdio = "stdio"
    http = "http"


@dataclass
class TranscribeArgs:
    uri: str
    lang: Optional[str] = field(default=None)
    verbose: bool = field(default=False)
    download_source: bool = field(default=False)
