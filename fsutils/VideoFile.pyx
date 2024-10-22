"""VideoFile.Video: Represents a video file. Has methods to extract metadata like fps, aspect ratio etc."""

import contextlib
import hashlib
import json
import os
import pickle
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, LiteralString

import cv2
from . import Exceptions
from . import FFProbe
from . import GenericFile
from . import ImageFile
from . import tools

cv2.setLogLevel(1)


class Video(GenericFile.File):
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

    _metadata: dict | None = None
    _info = None
    _stream = None

    def __init__(self, path: str | Path, *args, **kwargs) -> None:
        """Initialize a new VideoFile.Video object.

        Paramaters:
        -------------
            - `path (str)` : The absolute path to the video file.

        """
        super().__init__(path, *args, **kwargs)
        del self._content

    @property
    def metadata(self) -> dict | None:
        if not self._metadata:
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
            except subprocess.CalledProcessError:
                print(f"Failed to run ffprobe on {self.path}.", file=sys.stderr)
                self._metadata = {}
        return self._metadata

    @property
    def tags(self) -> dict:
        return self.metadata.get("tags", {}) if self.metadata else {}

    @property
    def bitrate(self) -> int:
        """Extract the bitrate/s with ffprobe."""
        try:
            return round(int(self.metadata.get("bit_rate", -1)))
        except ZeroDivisionError:
            if self.is_corrupt:
                print(f"\033[31m{self.name} is corrupt!\033[0m")
            return 0

    @property
    def bitrate_human(self) -> str | None:
        """Return the bitrate in a human readable format."""
        if self.bitrate is not None and self.bitrate > 0:
            return tools.format_bytes(self.bitrate)
        return None

    @property
    def duration(self) -> int:
        return round(float(self.metadata.get("duration", 0)))

    @property
    def capture_date(self) -> datetime:
        """Return the capture date of the file."""
        capture_date = str(
            self.tags.get("creation_time") or datetime.fromtimestamp(self.stat().st_mtime)
        ).split(".")[0]
        return datetime.fromisoformat(capture_date)

    @property
    def codec(self) -> str | None:
        """Codec eg `H264` | `H265`."""
        return self.ffprobe.codec()

    @property
    def dimensions(self) -> tuple[int, int] | None:
        """Return width and height of the video `(1920x1080)`."""
        return self.ffprobe.frame_size()

    @property
    def is_corrupt(self) -> bool:
        """Check if the video is corrupt."""
        try:
            cap = cv2.VideoCapture(self.path)
            return cap.isOpened()
        except (OSError, SyntaxError):
            return True  # VideoFile.Video is corrupt
        except KeyboardInterrupt:
            sys.exit(0)

    @property
    def ffprobe(self) -> FFProbe.FFStream:
        """Return the first video stream."""
        try:
            return next(
                stream
                for stream in FFProbe.FFProbe(str(self.resolve())).streams
                if stream.is_video()
            )
        except StopIteration:
            if self.is_corrupt:
                raise Exceptions.CorruptMediaError(
                    f"{self.absolute()} is corrupt."
                ) from StopIteration
        except IndexError:
            if self.is_corrupt:
                raise Exceptions.CorruptMediaError(f"{self.absolute()} is corrupt.") from IndexError
            raise Exceptions.FFProbeError(
                f"FFprobe did not find any video streams for {self.path}."
            ) from IndexError

    @property
    def fps(self) -> int:
        """Return the frames per second of the video."""
        return self.ffprobe.frame_rate()

    @property
    def num_frames(self) -> int:
        """Return the number of frames in the video."""
        return self.ffprobe.frames()

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

    def make_gif(self, scale=640, fps=24, **kwargs: Any) -> ImageFile.Img:
        """Convert the video to a gif using FFMPEG.

        Parameters
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

        Returns
        --------
            - `ImageFile.Img` : New `ImageFile.Img` object of the gif created from this video file.
        """
        output = kwargs.get("output_path", f'{self.parent}/{self.prefix}{".gif"}')
        output_path = Path(output)
        if output_path.exists():
            return ImageFile.Img(output_path)
        subprocess.check_output(
            [
                "ffmpeg",
                "-i",
                f"{self.path}",
                "-vf",
                f"fps={fps},scale=-1:{scale!s}:flags=lanczos",
                f"{output_path}",
                "-loglevel",
                "quiet",
            ]
        )
        # Other options: "-pix_fmt","rgb24" |
        return ImageFile.Img(output_path)
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
        output_dir = kwargs.get("output", f"{self.name}-frames/")
        Path.mkdir(output_dir, parents=True, exist_ok=True)
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
                    os.path.join(f"{self.name}-frames", f"frame{frame_duration_formatted}.jpg"),
                    frame,
                )
                # drop the duration spot from the list, since this duration spot is already saved
                with contextlib.suppress(IndexError):
                    frametime_refs.pop(0)
            # increment the frame count
            count += 1

    def compress(self, **kwargs: Any) -> "Video":
        """Compress video using x265 codec with crf 18.

        Keyword Arguments:
        ----------------
            - `output` : Save compressed video to this path

        Examples
        --------
        >>> vid.compress(output="~/Videos/compressed_video.mp4", codec="hevc_nvenc")
        """
        output = kwargs.get("output") or f"{self.parent}/_{self.prefix}.mp4"
        output_path = Path(output).resolve()
        fps = self.fps if self.fps < 200 else 30
        for keyword, value in kwargs.items():
            if "-r" in kwargs or "fps" in keyword:
                fps = value
        print(fps)

        ffmpeg_cmd = [
            "ffmpeg",
            "-hwaccel",
            "cuda",
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
            "-c:a",
            "copy",
            "-v",
            kwargs.get("loglevel", "quiet"),
            "-y",
            "-stats",
            str(output_path),
        ]
        print(subprocess.check_output(ffmpeg_cmd))
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
        return f"{self.__class__.__name__}(name={self.name}, size={self.size_human})".format(
            **vars(self)
        )

    def __hash__(self) -> int:
        return hash(self.sha256())
        # return hash((self.bitrate, self.duration, self.codec, self.fps, self.md5_checksum(4096)))
    def __format__(self, format_spec: str, /) -> str:
        """Return the object in tabular format."""
        name = self.name
        iterations = 0
        while len(name) > 20 and iterations < 5:  # Protection from infinite loop
            if "-" in name:
                name = name.split("-")[-1]
            else:
                name = ".".join([name.split(".")[0], name.split(".")[-1]])
            iterations += 1
        return f"{name.strip():<25} | {self.num_frames:<10} | {self.bitrate_human:<10} | {self.size_human:<10} | {self.codec:<10} | {self.duration:<10} | {self.fps:<10} | {self.dimensions!s:<10}"

    @staticmethod
    def fmtheader() -> str | LiteralString:
        template = "{:<25} | {:<10} | {:<10} | {:<10} | {:<10} | {:<10} | {:<10} | {:<10}\n"
        header = template.format(
            "File", "Num Frames", "Bitrate", "Size", "Codec", "Duration", "FPS", "Dimensions"
        )
        linebreak = template.format(
            "-" * 25, "-" * 10, "-" * 10, "-" * 10, "-" * 10, "-" * 10, "-" * 10, "-" * 10
        )
        return f"\033[1m{header}\033[0m{linebreak}"