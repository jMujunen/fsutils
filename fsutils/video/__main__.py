"""Handle command line operations related to videos.

Commands:
---------
- `makegif` : Create a GIF from a video file.
- `info` : Display information about one or more video files.
- `compress` : Compress a video file.


Example usage:
--------------
>>> # GIF
fstuils video makegif input_video.mp4  --scale 750 --fps 15 -o output_video.gif
# Info
fstuils video info ~/Videos/*.mp4
# Compress/transcode
fstuils video compress video.mp4 --output=/path/to/result.MOV

"""

import argparse
import contextlib
from typing import Any

from ThreadPoolHelper import Pool

from ..utils.mimecfg import FILE_TYPES
from .VideoFile import Video

video_types = tuple(FILE_TYPES["video"])


def parse_args() -> tuple[argparse.Namespace, argparse.ArgumentParser]:
    parser = argparse.ArgumentParser("Video related operations")
    subparsers = parser.add_subparsers(help="Actions", dest="action")
    makegif = subparsers.add_parser("makegif", help="Create GIF from video")
    # Create a parser for the "makegif" category under "video"

    makegif.add_argument(
        "PATH",
        nargs="+",
        type=str,
        help="Video path",
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
    # Create a parser for the "info" category under  "video
    # -------- Information -----------
    video_info = subparsers.add_parser(
        "info",
        help="Display information about a video",
    )
    video_info.add_argument(
        "PATH",
        nargs="+",
        type=str,
        help="Video path",
    )

    # -------- Compression -----------
    compress = subparsers.add_parser(
        "compress",
        help="Compress a video file",
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
    return parser.parse_args(), parser


def main() -> Any:
    args, parser = parse_args()
    try:
        action = args.action
        PATH = args.PATH
    except AttributeError:
        parser.print_help()
        return 1
    kwargs = {}
    with contextlib.suppress(AttributeError):
        kwargs = parse_kwargs(*args.kwargs)
    videos = [Video(vid) for vid in PATH if vid.endswith(video_types)]
    print(kwargs)

    match action:
        case "makegif":
            if "quality" in kwargs:
                for vid in videos:
                    vid.make_hq_gif(**kwargs)
                return 0

            for vid in videos:
                vid.make_gif(**kwargs)
            return 0
        case "info":
            print(Video.fmtheader())
            print("\n".join(sorted(Pool().execute(format, videos, progress_bar=False))))
            return 0
        case "compress":
            for vid in videos:
                try:
                    vid.compress(**kwargs)
                except Exception as e:
                    print(f"{e!r}")
            return 0
        case _:
            print("\033[31mError:\033[0m ", action, "is not a known action")
            return 1


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
    main()
    args = parse_args()
