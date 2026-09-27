from gerardnico.transcribe import pillow_image
from tests.gerardnico.transcribe.test_utils import get_tests_dir


def test_get_image_extension():
    # Tiktok error that returns .image file
    image = get_tests_dir() / "fixtures" / "images" / "thumbnail.image"
    extension = pillow_image.get_image_extension(image)
    assert extension == ".jpg", "The image is a jpeg"
