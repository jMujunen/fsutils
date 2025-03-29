"""Video: Represents a video file. Has methods to extract metadata like fps, aspect ratio etc."""

import contextlib
import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
import cv2

from fsutils.file import File
from fsutils.img import Img
from fsutils.utils.tools import format_bytes, format_timedelta, frametimes
from fsutils.video.FFProbe import FFProbe, FFStream
from dataclasses import dataclass, field

cv2.setLogLevel(1)


@dataclass
class CompressOptions:
    hwaccel: str = "cuda"
    encoder: str = "hevc_nvenc"
    crf: int = 26
    qp: int = 28
    rc: str = "constqp"
    preset: str = "fast"
    tune: str = "hq"
    loglevel: str = "error"
    stats: str = ""
    output: str = field(default_factory=str, kw_only=True)

    @classmethod
    def from_dict(cls, options: dict[str, Any]) -> "CompressOptions":
        """Create an instance of CompressOptions from a dictionary."""
        return cls(**options)

    def cmd(self, input_file: str) -> list[str]:
        """Generate a command list for ffmpeg based on the options."""
        template = "ffmpeg -hwaccel {hwaccel} -i {input_file} -c:v {encoder} -crf {crf} -qp {qp} -rc {rc} -preset {preset} -tune {tune} -loglevel {loglevel} -y {output} {stats}"
        return template.format(input_file=input_file, **self.__dict__).split()


@dataclass
class FFMPEG_GIF_OPTIONS:
    """FFMPEG_GIF_OPTIONS class."""

    scale: int = 750
    fps: int = 15
    loglevel: str = "error"
    loop: int = -1
    output: str = field(default_factory=str, kw_only=True)

    def cmd(self, input_file: str) -> list[str]:
        """Generate a command list for ffmpeg based on the options."""

        template = "ffmpeg -i {input} -vf fps={fps},scale={scale!s}:-1:flags=lanczos -v {loglevel} -loop {loop} -y -stats {output}"
        return template.format(input_file=input_file, **self.__dict__).split()

        return template.format(input_file=input_file, **self.__dict__).split()


class Video(File, FFProbe):  # noqa: PLR0904
    """A class representing information about a video.

    | Method | Description |
    | :---------------- | :-------------|
    | `metadata()`     | Extract video metadata |
    | `compress()` | Compress the video using ffmpeg |
    | `make_gif(scale, fps, output)` | Create a gif from the video |
    | `extract_frames()` | Extract frames from the video |
    | `render()`       | Render the video using ffmpeg |
    | `trim()`         | Trim the video using ffmpeg |

    ---------------
    ### Attributes:
        - `path (str):` The absolute path to the file.
    -------------------
    ### Properties:
    -----------
        - `is_corrupt`
        - `duration`
        - `size`
        - `codec`
        - `dimensions`
        - `bitrate`
    """

    _metadata: FFStream | None = None
    _fmt: dict[str, Any] | None = None

    def __init__(self, path: str | Path, *args, **kwargs) -> None:
        """Initialize a new Video object.

        Paramaters:
        -------------
            - `path (str)` : The absolute path to the video file.

        """
        File.__init__(self, str(path), *args, **kwargs)
        FFProbe.__init__(self, path)
        # FFProbe.__init__(self, path)
        # vid_stream = FFProbe(path).streams[0]
        # FFStream.__init__(self, vid_stream.__dict__)

    @property
    def metadata(self) -> FFStream:
        """Extract the metadata of the video."""
        if self._metadata is None:
            probe = FFProbe(self.path)
            for stream in probe.streams:
                if stream.is_video():
                    self._metadata = stream
                    break
            else:
                raise ValueError(f"No video stream found in {self.name}")

        return self._metadata

    @property
    def bitrate(self) -> int:
        """Extract the bitrate/s with metadata."""
        try:
            return round(int(self.bit_rate))
        except ZeroDivisionError:
            if self.is_corrupt:
                print(f"\033[31m{self.name} is corrupt!\033[0m")
            return 0

    @property
    def bitrate_human(self) -> str | None:
        """Return the bitrate in a human readable format."""
        if self.bitrate is not None and self.bitrate > 0:
            return format_bytes(self.bitrate)
        return None

    @property
    def capture_date(self) -> datetime:
        """Return the capture date of the file."""
        try:
            date, time = self.tags.get("creation_time", "").split("T")
            year, month, day = date.split("-")
            hour, minute, second = time.split(".")[0].split(":")
            return datetime(
                int(year),
                int(month),
                int(day),
                int(hour),
                int(minute),
                int(second[:2]),
            )
        except (KeyError, ValueError, AttributeError):
            return self.mtime

    @property
    def codec(self) -> str | None:
        """Codec eg `H264` | `H265`."""
        return self.codec

    @property
    def dimensions(self) -> tuple[int, int] | None:
        """Return width and height of the video `(1920x1080)`."""
        return self.frame_size

    @property
    def is_corrupt(self) -> bool:
        """Check if the video is corrupt."""
        try:
            cap = cv2.VideoCapture(self.path)
            return not cap.isOpened()
        except (OSError, SyntaxError):
            return True  # Video is corrupt
        except KeyboardInterrupt:
            sys.exit(0)

    @property
    def fps(self) -> int:
        """Return the frames per second of the video."""
        enum, denum = map(int, self.avg_frame_rate.split("/"))
        return round(enum / denum)

    @property
    def num_frames(self) -> int:
        """Return the number of frames in the video."""
        num_frames = 0
        if hasattr(self, "nb_frames"):
            num_frames = self.nb_frames
        else:
            try:
                num_frames = round(cv2.VideoCapture(self.path).get(cv2.CAP_PROP_FRAME_COUNT))
                self.nb_frames = num_frames
            except Exception as e:
                print(f"Error getting num_frames with cv2: {e!r}")
        return num_frames

    def make_hq_gif(self, scale=640, fps=24, **kwargs) -> Img | None:
        """Convert the video to a high-quality gif using FFMPEG.

        Paramaters
        -----------
            scale : int
                The width of the output gif. The height will be calculated to maintain the aspect ratio.
            fps : int
                The frames per second of the output gif.
            **kwargs : dict
                Additional arguments to pass to FFMPEG.
        """
        _TMPFILE = "/tmp/palette.png"
        _fps = min(fps, self.fps)
        FILTERS = f"fps={_fps},scale={scale}:-1:flags=lanczos"

        output_path = Path(kwargs.get("output", f"{self.parent}/{self.prefix}{'.gif'}"))
        if not str(output_path).endswith(".gif"):
            output_path = output_path.with_suffix(".gif")

        if output_path.exists():
            if input("Overwrite existing file? (y/n): ").lower() in {"Y", "y", "yes"}:
                output_path.unlink()
            else:
                print("Not overwriting existing file")
                return Img(output_path)

        generate_palette_cmd = (
            f'ffmpeg -i {self.path} -vf "{FILTERS},palettegen" -y -v error  -stats {_TMPFILE}'
        )
        generate_gif_cmd = f'ffmpeg -i {self.path} -i {_TMPFILE} -lavfi "{FILTERS} [x]; [x][1:v] paletteuse" -y -v error {output_path}'
        try:
            subprocess.check_call(generate_palette_cmd, shell=True)
            subprocess.check_call(generate_gif_cmd, shell=True)
            result = Img(output_path)
            if result.exists():
                return result
        except Exception as e:
            print(f"\033[31mError:\033[0m{e!r}")
        return None

    def make_gif(self, scale=640, fps=15, loop=False, **kwargs: Any) -> Img:
        """Convert the video to a gif using FFMPEG.

        Parameters
        -----------
            - `scale` : int, optional (default is 500)
            - `fps`   : int, optional (default is 10)

            Breakdown:
            * `FPS` : Deault is 24 but the for smaller file sizes, try 6-10
            * `SCALE`  is the width of the output gif in pixels.
                - 500-1000 = high quality but larger file size.
                - 100-500   = medium quality and smaller file size.
                - 10-100    = low quality and smaller file size.

            * The default `fps | scale` of `24 | 500` means a decent quality gif.

        Returns
        --------
            - `Img` : New `Img` object of the gif created from this video file.
        """

        output = kwargs.get("output", f"{self.parent}/{self.prefix}{'.gif'}")
        output_path = Path(output)
        if output_path.exists():
            if input("Overwrite existing file? (y/n): ").lower() in {"Y", "y", "yes"}:
                output_path.unlink()
            else:
                print("Not overwriting existing file")
                return Img(output_path)

        subprocess.check_output([
            "ffmpeg",
            "-i",
            f"{self.path}",
            "-vf",
            f"fps={fps},scale={scale!s}:-1:flags=lanczos",
            "-v",
            "error",
            "-stats",
            f"{output_path}",
        ])
        return Img(output_path)

    def extract_frames(self, fps=1, **kwargs: Any) -> list[Img]:
        """Extract frames from video.

        Paramaters
        -----------
            - `fps` : Frames per second to extract (default is `1`)

        Kwargs:
        ------------------
            - `output` : Output directory for frames (default is `{filename}-frames/`)


        """
        # Define output
        output_dir = Path(kwargs.get("output", f"{self.name}-frames/"))
        Path.mkdir(output_dir, parents=True, exist_ok=True)
        cap = cv2.VideoCapture(self.path)
        # Init opencv video capture object and get properties
        clip_fps = round(cap.get(cv2.CAP_PROP_FPS))
        num_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        interval = round(min(clip_fps, fps))
        frametime_refs = frametimes(num_frames, clip_fps, interval)

        saved_frames = []
        count = 0
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            frametime = count / clip_fps
            try:
                # get the earliest duration to save
                closest_duration = frametime_refs[0]
            except IndexError:
                # the list is empty, all duration frames were saved
                break
            if frametime >= closest_duration:
                # if closest duration is less than or equals the frametime,
                # then save the frame
                output_path = Path(
                    output_dir, f"frame{format_timedelta(timedelta(seconds=frametime))}.jpg"
                )
                print(f"Writing frame {count} to {output_path}")
                cv2.imwrite(
                    str(output_path),
                    frame,
                )  # type: ignore
                saved_frames.append(Img(str(output_path)))
                # drop the duration spot from the list, since this duration spot is already saved
                with contextlib.suppress(IndexError):
                    frametime_refs.pop(0)
            # increment the frame count
            count += 1
        return saved_frames

    def subclip(self, start_: int, end_: int, output: str | Path) -> "Video":
        """Trim the video from start to end time (seconds).

        Parameters
        ----------
            - `start_ (int)`:  (default is 0)
            - `end_ int` : (default is 100)
            - `output (str)` : (default is current working directory)
        """

        template = "{}:{}"
        start = template.format(*divmod(start_, 60))
        end = template.format(*divmod(end_, 60))

        output_path = Path(output).resolve()
        subprocess.check_call(
            f"ffmpeg -ss {start} -to {end} -i {self!s} -codec copy -v quiet -y {output_path}",
            shell=True,
        )
        return Video(str(output_path))

    def compress(self, **kwargs: Any) -> "Video":
        """Transcode video.

        Keyword Arguments:
        ----------------
        The following default ffmpeg params can be modifed by specifying them as keyword arguments

        | Flag         | Default Parameters |
        | :-------     | ------------------:|
        | -c:v         | hevc_nvenc         |
        | -crf         | 26                 |
        | -qp          | 28                 |
        | -rc          | constqp            |
        | -preset      | fast               |
        | -tune        | hq                 |
        | -v           | error              |
        | --output     | ./origname.mp4     |

        Examples
        --------
        ```python
        # ffmpeg -i <input> -c:v hevc_nvenc -crf 18 -c:a copy -v quiet -y <output>
        vid.compress(output="~/Videos/compressed_video.mp4", codec="hevc_nvenc")
        ```
        """
        try:
            output = kwargs.pop("output")
        except KeyError:
            output = f"{self.parent}/_{self.prefix}.mp4"

        options = CompressOptions(**kwargs, output=os.path.expanduser(output))

        ffmpeg_cmd = options.cmd(self.path)
        print(subprocess.getoutput(" ".join(ffmpeg_cmd)))
        return Video(options.output)

    def render(self) -> None:
        """Render the video."""
        if os.environ.get("TERM") == "xterm-kitty":
            try:
                subprocess.call(["mpv", self.path])
            except Exception as e:
                print(f"Error: {e}")
        else:
            try:
                subprocess.call(["xdg-open", self.path])
            except Exception as e:
                print(f"Error: {e}")

    def __repr__(self) -> str:
        """Return a string representation of the file."""
        return f"{self.__class__.__name__}(name={self.name}, size={self.size_human})".format(
            **vars(self)
        )

    def sha256(self) -> bytes:
        return super().sha256()

    def hash(self) -> int:
        """Return the hash of the file."""
        return super().__hash__()

    def __format__(self, format_spec: str, /) -> str:
        """Return the object in tabular format."""
        template = "{:<25} | {:<10} | {:<10} | {:<10} | {:<10} | {:<10} | {:<10} | {!s:<10}"
        name = self.name
        iterations = 0
        while len(name) > 20 and iterations < 5:  # Protection from infinite loop
            if "-" in name:
                name = name.split("-")[-1]
            else:
                name = ".".join([name.split(".")[0], name.split(".")[-1]])
            iterations += 1
        return template.format(
            name.strip(),
            self.num_frames,
            self.bitrate_human,
            self.size_human,
            self.codec,
            self.duration,
            self.frame_rate,
            self.dimensions,
        )

    @staticmethod
    def fmtheader() -> str:
        template = "{:<25} | {:<10} | {:<10} | {:<10} | {:<10} | {:<10} | {:<10} | {:<10}\n"
        header = template.format(
            "File", "Num Frames", "Bitrate", "Size", "Codec", "Duration", "FPS", "Dimensions"
        )
        linebreak = template.format(
            "-" * 25, "-" * 10, "-" * 10, "-" * 10, "-" * 10, "-" * 10, "-" * 10, "-" * 10
        )
        return f"\033[1m{header}\033[0m{linebreak}"
