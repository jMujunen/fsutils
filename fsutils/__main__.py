#!/usr/bin/env python3
import argparse

from fsutils import Video  # , File, Dir, obj, Exe
from Color import cprint, fg, style


def parse_args():
    # Create the main parser
    main_parser = argparse.ArgumentParser(
        prog="fstuils", description="A collection of command line utilities"
    )
    subparsers = main_parser.add_subparsers(help="commands", dest="command")

    # Create the parser for the "video" command
    video_parser = subparsers.add_parser("video", help="Video related operations")
    video_subparsers = video_parser.add_subparsers(help="video commands", dest="video_command")
    # Create a parser for the "makegif" command under "video"
    makegif_parser = video_subparsers.add_parser(
        "makegif",
        help="Create GIF from video",
    )
    makegif_parser.add_argument(
        "file",
        help="Input video file",
        type=str,
    )
    makegif_parser.add_argument(
        "--fps",
        type=int,
        default=24,
    )
    makegif_parser.add_argument(
        "--scale",
        type=int,
        default=500,
        help="Scale factor for the gif - (100-1000 is usually good).",
    )
    makegif_parser.add_argument(
        "-o",
        "--output",
        help="Output file",
        type=str,
        default="./output.gif",
    )

    video_info = video_subparsers.add_parser(
        "info",
        help="Display information about a video",
    )
    video_info.add_argument(
        "file",
        type=str,
        help="Input Video File",
    )
    video_info.add_argument(
        "--codec",
        help="Display codec information",
        action="store_true",
    )
    video_info.add_argument(
        "--dimensions",
        help="Display video dimensions",
        action="store_true",
    )
    video_info.add_argument(
        "--duration",
        help="Display video duration",
        action="store_true",
    )
    video_info.add_argument(
        "--bitrate",
        help="Display video bitrate",
        action="store_true",
    )
    video_info.add_argument(
        "--size",
        help="Display size of file in bytes",
        action="store_true",
    )
    video_info.add_argument(
        "--capture_date",
        help="Display capture date of video",
        action="store_true",
    )

    img_parser = subparsers.add_parser("img", help="Image related operations")
    img_subparsers = img_parser.add_subparsers(help="Image commands", dest="image_command")
    image_info__parser = img_subparsers.add_parser(
        "info",
        help="Create GIF from video",
    )

    resize_parser = img_subparsers.add_parser("resize", help="Resize an image")
    resize_parser.add_argument("--width", type=int, required=True)
    resize_parser.add_argument("--height", type=int, required=False)

    # image_parser.

    return main_parser.parse_args()


def log_parser(arguments: argparse.Namespace):
    pass


def dir_parser(arguments: argparse.Namespace) -> int:
    return 1


def image_parser(arguments: argparse.Namespace):
    pass


def video_parser(arguments: argparse.Namespace) -> int:
    specs = {
        "codec": Video(arguments.file).codec,
        "dimensions": Video(arguments.file).dimentions,
        "duration": Video(arguments.file).duration,
        "bitrate": Video(arguments.file).bitrate,
        "size": Video(arguments.file).size,
        "capture_date": Video(arguments.file).capture_date,
        "info": Video(arguments.file).info,
    }
    if arguments.video_command == "makegif":
        return Video(arguments.file).make_gif(arguments.scale, arguments.fps, arguments.output)
    elif arguments.video_command == "info":
        print(Video(arguments.file).info)
        for arg, value in arguments.__dict__.items():
            if arg in specs.keys() and value:
                print(f"{arg}: {specs[arg]}")
        return 0
    return 1


if __name__ == "__main__":
    args = parse_args()
    cprint(args, style.bold)
    if args.command == "video":
        video_parser(args)
