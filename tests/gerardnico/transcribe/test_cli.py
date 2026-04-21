from src.gerardnico.transcribe.cli import parse_uri


def test_url_parsing_file():
    uri_info = parse_uri("file.mp3")
    assert not uri_info.service_name  # test emptiness
