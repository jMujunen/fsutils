#!/usr/bin/env python3
import argparse

from fsutils import Video  # , File, Dir, obj, Exe


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
        nargs="+",
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
    video_info.add_argument(
        "--fps",
        help="Display frames per second of video",
        action="store_true",
    )
    video_info.add_argument(
        "--all",
        help="Display all information about a video",
        action="store_true",
    )

    img_parser = subparsers.add_parser("img", help="Image related operations")
    img_subparsers = img_parser.add_subparsers(help="Image commands", dest="image_command")
    img_subparsers.add_parser(
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


def video_info_all(video: Video) -> str:
    return f"""
        Codec: {video.codec}
        Dimensions: {video.dimensions}
        Duration: {video.duration}
        Bitrate: {video.bitrate_human}
        Size: {video.size_human}
        Frame rate: {video.ffprobe().frame_rate()}
        Aspect ratio: {video.ffprobe().aspect_ratio()}
        Capture date: {video.capture_date}
    """


def video_parser(arguments: argparse.Namespace) -> int:
    specs = {
        "codec": lambda file: Video(file).codec,
        "dimensions": lambda file: Video(file).dimensions,
        "duration": lambda file: Video(file).duration,
        "bitrate": lambda file: Video(file).bitrate,
        "size": lambda file: Video(file).size,
        "capture_date": lambda file: (file).capture_date,
        "info": lambda file: Video(file).info,
        "fps": lambda file: Video(file).ffprobe().frame_rate(),
        "all": lambda file: video_info_all(Video(file)),
    }
    if arguments.video_command == "makegif":
        return Video(arguments.file).make_gif(arguments.scale, arguments.fps, arguments.output)
    elif arguments.video_command == "info":
        if isinstance(arguments.file, str):
            files = [arguments.file]
        else:
            files = arguments.file
        for file in files:
            for arg, value in arguments.__dict__.items():
                if arg in specs.keys() and value:
                    print(f"{arg}: {specs[arg](file)}")
        return 0
    return 1


if __name__ == "__main__":
    args = parse_args()
    if args.command is None:
        args.print_help()
        exit(1)
    if args.command == "video":
        video_parser(args)
