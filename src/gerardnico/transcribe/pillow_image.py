from pathlib import Path

from PIL import Image, UnidentifiedImageError

# Pillow's Image.registered_extensions() maps extension -> format, and picks
# arbitrary/legacy extensions first when inverted (e.g. JPEG -> ".jfif").
# Override with the extension people actually expect for common formats.
PREFERRED_EXTENSIONS = {
    "JPEG": ".jpg",
    "PNG": ".png",
    "GIF": ".gif",
    "BMP": ".bmp",
    "WEBP": ".webp",
    "TIFF": ".tiff",
    "MPO": ".jpg",  # multi-picture JPEG (common in some phone photos)
}


def get_image_extension(path: Path) -> str | None:
    """
    Pillow inspects the file's actual content (headers/magic bytes)
    so extension name may be not correct
    """
    try:
        with Image.open(path) as img:
            if img.format is None:
                return None

            if img.format in PREFERRED_EXTENSIONS:
                return PREFERRED_EXTENSIONS[img.format]

            for ext, registered_fmt in Image.registered_extensions().items():
                if registered_fmt == img.format:
                    return ext

            return f".{img.format.lower()}"
    except UnidentifiedImageError:
        # could not open/detect it as a file
        return None
