"""Video: Represents a video file. Has methods to extract metadata like fps, aspect ratio etc."""

import contextlib
import hashlib
import json
import os
import pickle

os.environ["LOG_LEVEL"] = "0"
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import cv2
from size import Size

from .Exceptions import CorruptMediaError, FFProbeError
from .FFProbe import FFProbe, FFStream
from .GenericFile import File
from .tools import format_timedelta, frametimes


class Video(File):
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

    _tags: dict[str, str] | None = None
    _fps: float
    _num_frames: int
    _duration: float
    _dimensions: tuple[int, int]
    _bitrate: int
    _bitrate_human: str
    _metadata: dict[str, Any]
    _capture_date: datetime

    def __init__(self, path: str, lazy_load=True) -> None:
        """Initialize a new Video object.

        Paramaters:
        -------------
            - `path (str)` : The absolute path to the video file.
            - `lazy_load (bool)` : Whether or not to load metadata lazily. Defaults to True.
        """
        super().__init__(path)

    @property
    def metadata(self) -> dict:
        if not hasattr(self, "_metadata"):
            ffprobe_cmd = [
                "ffprobe",
                "-v",
                "quiet",
                "-print_format",
                "json",
                "-show_format",
                self.path,
            ]
            try:
                result = subprocess.run(ffprobe_cmd, check=True, capture_output=True, text=True)
                ffprobe_output = result.stdout
                if ffprobe_output is None:
                    return {}
                self._metadata = json.loads(ffprobe_output).get("format")
                # self.__dict__.update(self._metadata)
            except subprocess.CalledProcessError:
                print(f"Failed to run ffprobe on {self.path}.", file=sys.stderr)
                self._metadata = {}
        return self._metadata

    @property
    def tags(self) -> dict[str, str]:
        return self.metadata.get("tags", {})

    @property
    def fps(self) -> float:
        """Return the frames per second of the video."""
        if not hasattr(self, "_fps"):
            self.__setattr__("_fps", self.ffprobe.frame_rate())
        return self._fps

    @property
    def num_frames(self) -> int:
        """Return the number of frames in the video."""
        if not hasattr(self, "_num_frames"):
            self.__setattr__("_num_frames", self.metadata.get("nb_frames", self.ffprobe.frames()))
        return self._num_frames

    @property
    def bitrate(self) -> int:
        """Extract the bitrate/s with ffprobe."""
        try:
            return self.metadata.get("bitrate", round(int(self.metadata.get("bit_rate", -1))))
        except ZeroDivisionError:
            if self.is_corrupt:
                print(f"\033[31m{self.basename} is corrupt!\033[0m")
            return 0

    @property
    def bitrate_human(self) -> str:
        """Return the bitrate in a human readable format."""
        if self.bitrate is not None and self.bitrate > 0:
            return str(Size(self.bitrate))
        return "N/A"

    @property
    def duration(self) -> int:
        return self.metadata.get("duration", round(float(self.metadata.get("duration", 0))))

    @property
    def dimensions(self) -> tuple[int, int] | None:
        """Return width and height of the video `(1920x1080)`."""
        return self.__dict__.get("_dimensions", self.ffprobe.frame_size())

    @property
    def capture_date(self) -> datetime:
        """Return the capture date of the file."""
        if hasattr(self, "_capture_date"):
            return self._capture_date
        capture_date = str(
            self.tags.get("creation_time") or datetime.fromtimestamp(os.path.getmtime(self.path))
        ).split(".")[0]
        self._capture_date = datetime.fromisoformat(capture_date)
        return self._capture_date

    @property
    def codec(self) -> str | None:
        """Codec eg `H264` | `H265`."""
        return self.ffprobe.codec()

    @property
    def is_corrupt(self) -> bool:
        """Check if the video is corrupt."""
        try:
            cap = cv2.VideoCapture(self.path)
            if cap.isOpened():
                cap.release()
                return False  # Video is not corrupted
            return True
        except (OSError, SyntaxError):
            return True  # Video is corrupt
        except KeyboardInterrupt:
            sys.exit(0)

    @property
    def ffprobe(self) -> FFStream:
        """Return the first video stream."""
        try:
            return next(stream for stream in FFProbe(self.path).streams if stream.is_video())
        except IndexError:
            if self.is_corrupt:
                raise CorruptMediaError(f"{self.path} is corrupt.") from IndexError
            raise FFProbeError(
                f"FFprobe did not find any video streams for {self.path}."
            ) from IndexError

    def render(self) -> None:
        """Render the video using `mpv` | `vo` protocol if available with xdg-open as fallback."""
        if os.environ.get("TERM") == "xterm-kitty":
            try:
                subprocess.call(
                    [
                        "mpv",
                        "--vo=kitty",
                        "--vo-kitty-use-shm=yes",
                        "--hwdec=cuda",
                        "--cuda-decode-device=0",
                        self.path,
                    ]
                )
            except Exception as e:
                print(f"Error: {e}")
        else:
            try:
                subprocess.call(["xdg-open", self.path])
            except Exception as e:
                print(f"Error: {e}")

    def make_gif(
        self,
        scale: int | str | tuple[int, int] = 640,
        fps=24,
        **kwargs: Any,
    ):
        """Convert the video to a gif using FFMPEG.

        Parameters:
        -----------
            - `scale` : int, optional (default is 500)
            - `fps`   : int, optional (default is 10)
            - `output_path` : str, optional (default is "./output.gif")
            - `bitrate` : int, optional (default is 3MB)

            Breakdown:
            * `FPS` : Deault is 24 but the for smaller file sizes, try 6-10
            * `SCALE`  is the width of the output gif in pixels.
                - 500-1000 = high quality but larger file size.
                - 100-500   = medium quality and smaller file size.
                - 10-100    = low quality and smaller file size.
            * `bitrate` : the bit rate of the video, in mb/s (100mb/s = 1080p | 10mb/s = 480p)

            * The default `fps | scale` of `24 | 500` means a decent quality gif.

        Returns:
        --------
            - `Img` : subprocess return code
        """
        # f"scale=-1:{str(scale)}:flags=lanczos",
        # subprocess.check_output(
        #     [
        #         "ffmpeg",
        #         "-i",
        #         f"{self.path}",
        #         "-vf",
        #         f"scale=-1:{str(scale)}:flags=lanczos",
        #         "-r",
        #         f"{str(fps)}",
        #         f"{output}",
        #         "-loglevel",
        #         "quiet",
        #     ]
        # )

        # Other options: "-pix_fmt","rgb24" |

        _cmd = [
            "ffmpeg",
            "-i",
            "{i}",
            "-vf",
            "scale=-1:{scale}:flags=lanczos",
            "-y",
            "-v",
            "error",
            "{output}",
        ]

        _cmd2 = [
            "ffmpeg",
            "-i",
            "{in}",
            "-vf",
            "framerate={fps}",
            "-s",
            "{scale",
            "-y",
            "-v",
            "error",
            "{output}",
        ]
        # cmd = _cmd.format(**kwargs)
        # match kwargs:
        #     case {"output": value}:

        # output = kwargs.get("output", os.path.join(self.dir_name, f"{self.filename[:-4]}.gif"))
        # if isinstance(scale, int):
        #     w = scale
        #     h = round(scale * 0.5625)
        # elif isinstance(scale, tuple):
        #     w, h = scale
        # else:
        #     raise ValueError(f"{scale} is not a valid value for scale")
        # scale = f"{w}x{h}"
        # match kwargs.keys():
        #     case _:
        #         pass
        # subprocess.check_output(
        #     [
        #         "ffmpeg",
        #         "-i",
        #         self.path,
        #         # "-vf",
        #         # f"fps={fps},scale=-1:{str(scale)}:flags=lanczos",
        #         "-vf",
        #         '"framerate=12"' "-r",
        #         str(fps),
        #         "-s",
        #         str(scale),
        #         "-c:v",
        #         "gif",
        #         "-pix_fmt",
        #         "rgb8",
        #         "-y",
        #         output,
        #         "-v",
        #         "error",
        #     ]
        # )

        return self

    def extract_frames(self, fps=1, **kwargs: Any) -> None:
        """Extract frames from video.

        Paramaters
        -----------
            - `fps` : Frames per second to extract (default is `1`)

        Kwargs:
        ------------------
            - `output` : Output directory for frames (default is `{filename}-frames/`)


        """
        # Define output
        output_dir = kwargs.get("output", f"{self.filename}-frames/")
        os.makedirs(output_dir, exist_ok=True)
        # Init opencv video capture object and get properties
        cap = cv2.VideoCapture(self.path)
        clip_fps = round(cap.get(cv2.CAP_PROP_FPS))
        num_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        interval = round(min(clip_fps, fps))
        frametime_refs = frametimes(num_frames, clip_fps, interval)

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
                frame_duration_formatted = format_timedelta(timedelta(seconds=frametime))
                cv2.imwrite(
                    os.path.join(f"{self.filename}-frames", f"frame{frame_duration_formatted}.jpg"),
                    frame,
                )
                # drop the duration spot from the list, since this duration spot is already saved
                with contextlib.suppress(IndexError):
                    frametime_refs.pop(0)
            # increment the frame count
            count += 1

    def trim(self, start_: int = 0, end_: int = 100, output: str | Path | None = None) -> int:
        """Trim the video from start to end time (seconds).

        Parameters:
        ----------
            - `start_ (int)`:  (default is 0)
            - `end_ int` : (default is 100)
            - `output (str)` : (default is current working directory)
        """

        output_path = output if output else self.path[:-4] + f"_trimmed.{self.extension}"
        return subprocess.call(
            f"ffmpeg -ss mm:ss -to mm2:ss2 -i {self.path} -codec copy {output_path}"
        )

    def compress(self, **kwargs: Any) -> "Video":
        """Compress video using x265 codec with crf 18.

        Keyword Arguments:
        ----------------
            - `output` : Save compressed video to this path

        Examples
        --------
        >>> compress(output="~/Videos/compressed_video.mp4", codec="hevc_nvenc")
        """
        output_path = kwargs.get("output") or os.path.join(self.dir_name, f"_{self.basename}")
        subprocess.check_output(
            [
                "ffmpeg",
                "-i",
                self.path,
                "-c:v",
                kwargs.get("codec", "hevc_nvenc"),
                "-crf",
                kwargs.get("crf", "20"),
                "-qp",
                kwargs.get("qp", "24"),
                "-rc",
                "constqp",
                "-preset",
                kwargs.get("preset", "medium"),
                "-tune",
                kwargs.get("tune", "hq"),
                "-r",
                kwargs.get("fps", str(self.fps)),
                "-c:a",
                "copy",
                # "-b:a",
                # "128k",
                "-v",
                kwargs.get("loglevel", "quiet"),
                "-y",
                "-stats",
                output_path,
            ],
        )
        return Video(output_path)

    def sha256(self) -> str:
        serialized_object = pickle.dumps(
            {
                "md5": self.md5_checksum(),
                "size": self.size,
                "fps": self.fps,
                "bitrate": self.bitrate,
                "codec": self.codec,
                "duration": self.duration,
            }
        )
        return hashlib.sha256(serialized_object).hexdigest()

    def __repr__(self) -> str:
        """Return a string representation of the file."""
        return f"{self.__class__.__name__}(name={self.basename}, size={self.size_human})".format(
            **vars(self)
        )

    def __hash__(self) -> int:
        return hash((self.bitrate, self.duration, self.codec, self.fps, self.md5_checksum(8196)))

    def __format__(self, format_spec: str, /) -> str:
        """Return the object in tabular format."""
        name = self.basename
        iterations = 0
        while len(name) > 20 and iterations < 5:  # Protection from infinite loop
            if "-" in name:
                name = name.split("-")[-1]
            else:
                name = ".".join([name.split(".")[0], name.split(".")[-1]])
            iterations += 1
        return f"{name.strip():<25} | {self.num_frames:<10} | {self.bitrate_human:<10} | {self.size_human:<10} | {self.codec:<10} | {self.duration:<10} | {self.fps:<10} | {self.dimensions!s:<10}"

    @staticmethod
    def fmtheader() -> str:
        template = "{:<25} | {:<10} | {:<10} | {:<10} | {:<10} | {:<10} | {:<10} | {:<10}"
        header = template.format(
            "File", "Num Frames", "Bitrate", "Size", "Codec", "Duration", "FPS", "Dimensions"
        )
        linebreak = template.format(
            "-" * 25, "-" * 10, "-" * 10, "-" * 10, "-" * 10, "-" * 10, "-" * 10, "-" * 10
        )
        return f"\033[1m{header}\033[0m\n{linebreak}"
