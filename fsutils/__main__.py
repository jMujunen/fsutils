#!/usr/bin/env python3
import argparse

from .VideoFile import Video


def parse_args():
    # ======== MAIN PARSER =============
    main_parser = argparse.ArgumentParser(
        prog="fstuils", description="A collection of command line utilities"
    )
    subparsers = main_parser.add_subparsers(help="commands", dest="command")
    # Create the parser for the "video" command

    # |======== Video Parser =========|
    video_parser = subparsers.add_parser("video", help="Video related operations")
    video_subparsers = video_parser.add_subparsers(help="video commands", dest="video_command")
    # Create a parser for the "makegif" command under "video"
    video_makegif_parser = video_subparsers.add_parser(
        "makegif",
        help="Create GIF from video",
    )
    video_makegif_parser.add_argument(
        "file",
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
        type=int,
        default=500,
        help="Scale factor for the gif - (100-1000 is usually good).",
    )
    video_makegif_parser.add_argument(
        "-o",
        "--output",
        help="Output file",
        type=str,
        default="./output.gif",
    )
    # -------- Information -----------
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
    # -------- Compression -----------
    video_compress_parser = video_subparsers.add_parser(
        "compress",
        help="Compress a video file",
    )
    video_compress_parser.add_argument("file", type=str, help="Input Video File")
    video_compress_parser.add_argument(
        "-o ",
        "--output",
        type=str,
        help="Save to this path",
    )
    video_compress_parser.add_argument(
        "-c",
        "--clean",
        type=str,
        help="Remove the old file after sucessfull compression",
    )
    # |=========== Image Parser ==============|
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


def video_parser(arguments: argparse.Namespace) -> int:
    """Handle command line operations related to videos.

    Commands:
    ---------
        - `makegif` : Create a GIF from a video file.
        - `info` : Display information about one or more video files.
        - `compress` : Compress a video file.


    Example usage:
    --------------
    >>> fstuils video makegif input_video.mp4 --scale 750 --fps 15 -o output_video.gif
        fstuils video info video1.mp4 video2.mp4 --codec --dimensions --duration
        fstuils video compress video.mp4 -o compressed_video.mp4 --clean old_video.mp4
    """

    def video_info_all(video: Video) -> str:
        return f"""
            {video.basename}
            ---------------
            Codec: {video.codec}
            Dimensions: {video.dimensions}
            Duration: {video.duration}
            Bitrate: {video.bitrate_human}
            Size: {video.size_human}
            Frame rate: {video.ffprobe().frame_rate()}
            Aspect ratio: {video.ffprobe().aspect_ratio()}
            Capture date: {video.capture_date}
        """

    specs = {
        "codec": lambda v: v.codec,
        "dimensions": lambda v: v.dimensions,
        "duration": lambda v: v.duration,
        "bitrate": lambda v: v.bitrate,
        "size": lambda v: v.size,
        "capture_date": lambda v: v.capture_date,
        "info": lambda v: v.info,
        "fps": lambda v: v.ffprobe().frame_rate(),
        "all": lambda v: video_info_all(v),
    }
    if arguments.video_command == "makegif" and isinstance(arguments.file, str):
        return (
            Video(arguments.file)
            .make_gif(arguments.scale, arguments.fps, arguments.output)
            .render()
        )

    elif arguments.video_command == "info":
        files = arguments.file
        if isinstance(arguments.file, str):
            files = [arguments.file]
        video_objects = [Video(i) for i in files]
        for vid in video_objects:
            # print(vid.basename)
            # print("--------------------------")
            for arg, value in arguments.__dict__.items():
                if arg in specs.keys() and value:
                    print(f"{arg}: {specs[arg](vid)}")
        return 0

    elif arguments.video_command == "compress":
        output_path = arguments.output or f"{arguments.file}_compressed.mp4"
        try:
            compressed = Video(arguments.file).compress(output=output_path)
            print(video_info_all(compressed))
            return 0
        except Exception as e:
            print(e)
            return 1
    return 0


if __name__ == "__main__":
    args = parse_args()
    if args.command is None:
        args.print_help()
        exit(1)
    if args.command == "video":
        video_parser(args)
