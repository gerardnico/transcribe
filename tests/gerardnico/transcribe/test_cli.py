from src.gerardnico.transcribe.cli import build_request, CliArgs


def test_url_parsing_file():
    cli_args = CliArgs(uri="file.mp3")
    request = build_request(cli_args)
    assert request.service_name == "file"
