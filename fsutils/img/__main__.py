"""Handle command line operations related to images.

Commands:
---------
- `makegif` : Create a GIF from a image file.
- `info` : Display information about one or more image files.
- `compress` : Compress a image file.


Example usage:
--------------
>>> # GIF
fstuils image makegif input_image.mp4  --scale 750 --fps 15 -o output_image.gif
# Info
fstuils image info ~/Imgs/*.mp4
# Compress/transcode
fstuils image compress image.mp4 --output=/path/to/result.MOV

"""

import argparse
import contextlib
from typing import Any

from ThreadPoolHelper import Pool

from ..utils.mimecfg import FILE_TYPES
from .ImageFile import Img

image_types = tuple(FILE_TYPES["img"])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser("Img related operations")
    subparsers = parser.add_subparsers(help="Actions", dest="action")
    makegif = subparsers.add_parser("makegif", help="Create GIF from image")
    # Create a parser for the "makegif" category under "image"

    makegif.add_argument(
        "PATH",
        nargs="+",
        type=str,
        help="Img path",
    )
    makegif.add_argument(
        "--fps",
        type=int,
        default=24,
    )
    makegif.add_argument(
        "--scale",
        # type=int | str,
        default=500,
        help="Scale factor for the gif - (100-1000 is usually good).",
    )
    makegif.add_argument(
        "kwargs",
        metavar="KEY=VALUE",
        nargs=argparse.REMAINDER,
        help="Optional keyword arguments: --key value",
    )
    # Create a parser for the "info" category under  "image
    # -------- Information -----------
    image_info = subparsers.add_parser(
        "info",
        help="Display information about a image",
    )
    image_info.add_argument(
        "PATH",
        nargs="+",
        type=str,
        help="Img path",
    )

    # -------- Compression -----------
    compress = subparsers.add_parser(
        "compress",
        help="Compress a image file",
    )
    compress.add_argument(
        "PATH",
        help="File(s) paths to compress",
        nargs="+",
        type=str,
    )
    compress.add_argument(
        "-c",
        "--clean",
        help="Remove the old file after successful compression",
        action="store_true",
        default=False,
    )
    compress.add_argument(
        "--options",
        help="List additional options",
        required=False,
        action="store_true",
    )
    compress.add_argument(
        "kwargs",
        nargs=argparse.REMAINDER,
        help="Additional arguments to pass to ffmpeg",
    )
    return parser.parse_args()


def main(images: list[Img], action: str, **kwargs) -> Any:
    match action:
        case "makegif":
            if "quality" in kwargs:
                for vid in images:
                    vid.make_hq_gif(**kwargs)
                return

            for vid in images:
                vid.make_gif(**kwargs)
        case "info":
            print(Img.fmtheader())
            print("\n".join(sorted(Pool().execute(format, images, progress_bar=False))))
        case "compress":
            for vid in images:
                try:
                    vid.compress(**kwargs)
                except Exception as e:
                    print(f"{e:!r}")
        case _:
            print("\033[31mError:\033[0m ", action, "is not a known action")


def parse_kwargs(*args) -> dict:
    kwargs_dict = {}
    for arg in args:
        if "=" not in arg:
            continue
        key, value = arg.split("=", 1)
        with contextlib.suppress(ValueError):
            value = int(value)  # Try to convert to integer if possible
        kwargs_dict[key.strip("-")] = value
    return kwargs_dict


if __name__ == "__main__":
    args = parse_args()
    print("VIDEOS: ", args.PATH)
    kwargs = {}
    with contextlib.suppress(AttributeError):
        kwargs = parse_kwargs(*args.kwargs)
    images = [Img(vid) for vid in args.PATH if vid.endswith(image_types)]
    print(kwargs)
    main(images=images, action=args.action, **kwargs)
