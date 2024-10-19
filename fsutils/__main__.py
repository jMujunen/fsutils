import argparse
import contextlib
import sys
from typing import Any

from ThreadPoolHelper import Pool

from VideoFile import Video


def parse_args() -> argparse.Namespace:
    # ======== MAIN PARSER =============
    main_parser = argparse.ArgumentParser(
        prog="fsutils", description="A collection of command line utilities"
    )
    subparsers = main_parser.add_subparsers(help="commands", dest="category")
    # Create the parser for the "video" category

    # |======== Video Parser =========|

    video_parser = subparsers.add_parser("video", help="Video related operations")
    video_subparsers = video_parser.add_subparsers(help="video commands", dest="action")
    # Create a parser for the "makegif" category under "video"
    video_makegif_parser = video_subparsers.add_parser(
        "makegif",
        help="Create GIF from video",
    )
    video_makegif_parser.add_argument(
        "PATH",
        help="Input video file",
        type=str,
    )
    video_makegif_parser.add_argument(
        "--fps",
        type=int,
        default=24,
    )
    video_makegif_parser.add_argument(
        "--scale",
        # type=int | str,
        default=500,
        help="Scale factor for the gif - (100-1000 is usually good).",
    )
    video_makegif_parser.add_argument(
        "kwargs",
        metavar="KEY=VALUE",
        nargs=argparse.REMAINDER,
        help="Optional keyword arguments: --key value",
    )
    # Create a parser for the "info" category under  "video
    # -------- Information -----------
    video_info = video_subparsers.add_parser(
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
    video_compress_parser = video_subparsers.add_parser(
        "compress",
        help="Compress a video file",
    )
    video_compress_parser.add_argument(
        "PATH",
        help="File(s) paths to compress",
        type=str,
    )
    video_compress_parser.add_argument(
        "-c",
        "--clean",
        help="Remove the old file after successful compression",
        action="store_true",
        default=False,
    )
    video_compress_parser.add_argument(
        "--options",
        help="List additional options",
        required=False,
        action="store_true",
    )
    video_compress_parser.add_argument(
        "kwargs",
        nargs=argparse.REMAINDER,
        help="Additional arguments to pass to ffmpeg",
    )
    # |=========== Image Parser ==============|
    img_parser = subparsers.add_parser("img", help="Image related operations")
    img_subparsers = img_parser.add_subparsers(help="Image commands", dest="action")
    img_info_parser = img_subparsers.add_parser(
        "info",
        help="img info",
    )
    # img_info_parser.add_argument(
    #     kwargs="{'nargs': '+'}",
    #     help="Additional arguments to pass to ffmpeg",
    # )
    img_info_parser.add_argument("PATH", help="File path")

    resize_parser = img_subparsers.add_parser("resize", help="Resize an image")
    resize_parser.add_argument("--width", type=int, required=True)
    resize_parser.add_argument("--height", type=int, required=False)

    # |=========== Dir Parser ==============|
    dir_parser = subparsers.add_parser("dir", help="Directory related operations")
    dir_subparsers = dir_parser.add_subparsers(help="Directory commands", dest="action")
    # dir_info = dir_subparsers.add_parser("info", help="Directory info")

    dir_serialize = dir_subparsers.add_parser("serialize", help="Serialize directory")
    dir_serialize.add_argument("PATH", help="Directory to serialize")
    dir_serialize.add_argument(
        "--refresh",
        "-r",
        action="store_true",
        help="Refresh the data if it exists",
        default=False,
    )
    return main_parser.parse_args()


def log_parser(arguments: argparse.Namespace) -> None:
    pass


def dir_parser(arguments: argparse.Namespace) -> int:
    return 1


def image_parser(arguments: argparse.Namespace) -> None:
    print(arguments)


def parse_kwargs(*args) -> dict:
    kwargs_dict = {}
    for arg in args:
        if "=" not in arg:
            continue
        key, value = arg.split("=", 1)
        with contextlib.suppress(ValueError):
            value = int(value)  # Try to convert to integer if possible
        kwargs_dict[key] = value
    return kwargs_dict


def video_parser(arguments: argparse.Namespace) -> Any:
    """Handle command line operations related to videos.

    Commands:
    ---------
        - `makegif` : Create a GIF from a video file.
        - `info` : Display information about one or more video files.
        - `compress` : Compress a video file.


    Example usage:
    --------------
    ```sh
        # Gif
        fstuils video makegif input_video.mp4  --scale 750 --fps 15 -o output_video.gif
        # Info
        fstuils video info ~/Videos/*.mp4
        # Compress/transcode
        fstuils video compress video.mp4 --output=/path/to/result.MOV
    ```
    """

    def action(videos: list[Video]) -> Any:
        match arguments.action:
            case "makegif":
                for vid in videos:
                    vid.make_gif(arguments.scale, arguments.fps)
                return 0
            case "info":
                print(Video.fmtheader())
                return print("\n".join(Pool().execute(format, videos, progress_bar=False)))
            case "compress":
                for vid in videos:
                    vid.compress(**kwargs)
                return 0
            case _:
                return f"Invalid video command: {arguments.video} {arguments.action}"

    videos = (
        [Video(file) for file in arguments.PATH if isinstance(Video(file), Video)]
        if isinstance(arguments.PATH, list)
        else [Video(arguments.PATH)]
    )
    with contextlib.suppress(AttributeError):
        kwargs = parse_kwargs(*arguments.kwargs)

    return action(videos)


if __name__ == "__main__":
    args = parse_args()
    print(vars(args))
    template = """{category}.{action}(
    path={PATH}, {kwargs}"""
    match args.category:
        case "video":
            sys.exit(video_parser(args))
        case "img":
            sys.exit(image_parser(args))
        case "dir":
            sys.exit(dir_parser(args))
        case _:
            sys.exit("Invalid category")
