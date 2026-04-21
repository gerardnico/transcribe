import os

from src.gerardnico.transcribe.cli import build_request, CliArgs


def test_file_url_request():
    cli_args = CliArgs(uri="file.mp3")
    request = build_request(cli_args)
    assert request.service_name == "file"

def test_tiktok_url_request():
    cli_args = CliArgs(uri="https://www.tiktok.com/@beanulaegzo/video/7630306225086876959")
    request = build_request(cli_args)
    assert request.service_name == "tiktok"
    home = os.environ.get('HOME')
    assert request.paths.runtime_directory == f"{home}/.transcribe/tiktok/beanulaegzo-7630306225086876959"
    assert request.paths.file_extension == "mp4"
