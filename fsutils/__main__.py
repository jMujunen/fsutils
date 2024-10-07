import argparse
from typing import Any

from Color import bg, cprint, fg, style
from ThreadPoolHelper import Pool

from .DirNode import obj
from .VideoFile import Video


def parse_args() -> argparse.Namespace:
    # ======== MAIN PARSER =============
    main_parser = argparse.ArgumentParser(
        prog="fsutils", description="A collection of command line utilities"
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
        # type=int | str,
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

    # -------- Compression -----------
    video_compress_parser = video_subparsers.add_parser(
        "compress",
        help="Compress a video file",
    )
    video_compress_parser.add_argument(
        "file",
        help="File(s) to compress",
        type=str,
    )
    video_compress_parser.add_argument(
        "-c",
        "--clean",
        help="Remove the old file after sucessfull compression",
        action="store_true",
        default=False,
    )
    video_compress_parser.add_argument(
        "--options",
        help="List additional options",
        required=False,
        action="store_true",
    )
    # video_compress_parser.add_argument(
    #     "--crf",
    #     type=int,
    #     help="Constant Rate Factor",
    #     required=False,
    # )
    # video_compress_parser.add_argument(
    #     "--qp",
    #     type=int,
    #     help="Quantization Parameter",
    #     required=False,
    # )
    # video_compress_parser.add_argument(
    #     "--preset",
    #     type=str,
    #     help="Preset for compression",
    #     required=False,
    # )
    # video_compress_parser.add_argument(
    #     "--loglevel",
    #     type=str,
    #     help="Output Log Level",
    #     required=False,
    # )
    video_compress_parser.add_argument(
        "kwargs",
        nargs=argparse.REMAINDER,
        help="Additional arguments to pass to ffmpeg",
    )
    # |=========== Image Parser ==============|
    img_parser = subparsers.add_parser("img", help="Image related operations")
    img_subparsers = img_parser.add_subparsers(help="Image commands", dest="image_command")
    img_info_parser = img_subparsers.add_parser(
        "info",
        help="img info",
    )
    # img_info_parser.add_argument(
    #     kwargs="{'nargs': '+'}",
    #     help="Additional arguments to pass to ffmpeg",
    # )
    img_info_parser.add_argument("FILE", help="File path")

    resize_parser = img_subparsers.add_parser("resize", help="Resize an image")
    resize_parser.add_argument("--width", type=int, required=True)
    resize_parser.add_argument("--height", type=int, required=False)

    # image_parser.

    return main_parser.parse_args()


def log_parser(arguments: argparse.Namespace) -> None:
    pass


def dir_parser(arguments: argparse.Namespace) -> int:
    return 1


def image_parser(arguments: argparse.Namespace) -> None:
    print(arguments)


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
    video = Video(arguments.file)
    print(*arguments.__dict__.items())
    mapping = {k: str(v) for k, v in arguments.__dict__.items()}
    cmd = [k for k, v in mapping.items() if v]
    print(
        f"{fg.gray}{arguments.command}.{arguments.video_command}{style.reset} {arguments.file} {style.bold}-> {style.reset}{fg.green}{arguments.output}{style.reset} args={fg.cyan}[fps={arguments.fps}, scale={arguments.scale}]{style.reset}"
    )

    match arguments.video_command:
        case "makegif":
            print("Making GIF")
            return video.make_gif(arguments.scale, arguments.fps, output=arguments.output)
        case "info":
            print("Info")
            return print(format(video))
        case "compress":
            print("Compress")
            return video.compress(**arguments.kwargs)
        case _:
            print("Invalid command for video operations.")
            return -1
    if arguments.video_command == "makegif" and isinstance(arguments.file, str):
        gif = Video(arguments.file).make_gif(
            arguments.scale, arguments.fps, output=arguments.output
        )
        gif.render()

    if arguments.video_command == "info":
        files = arguments.file
        if isinstance(arguments.file, str):
            files = [arguments.file]
        video_objects = [obj(i) for i in files if isinstance(obj(i), Video)]
        pool = Pool()
        print(Video.fmtheader())
        print("\n".join(pool.execute(format, video_objects, progress_bar=False)))
    elif arguments.video_command == "compress":
        vid = Video(arguments.file)
        if isinstance(arguments.file, str):
            files = [arguments.file]
        kwargs = {item.split("=")[0].strip("--"): item.split("=")[1] for item in arguments.kwargs}  # noqa
        result = vid.compress(**kwargs)
        print(format(result, "header"))
    return 0


if __name__ == "__main__":
    args = parse_args()
    if args.command is None:
        print("Invalid")
    if args.command == "video":
        video_parser(args)
    elif args.command == "img":
        image_parser(args)
