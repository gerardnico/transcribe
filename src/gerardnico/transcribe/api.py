from dataclasses import dataclass
from typing import Optional, List

@dataclass
class Paths:
    runtime_directory: str
    file_name: str = None
    file_extension: str = None
    video_path: str = None
    # The resulting audio file path
    audio_path: str = None


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


