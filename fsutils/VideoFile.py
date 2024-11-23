"""Video: Represents a video file. Has methods to extract metadata like fps, aspect ratio etc."""

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
from rich.console import Console
from rich.table import Table, box

from fsutils.compiled._GenericFile import File
from fsutils.Exceptions import CorruptMediaError, FFProbeError
from fsutils.FFProbe import FFProbe, FFStream
from fsutils.ImageFile import Img
from fsutils.tools import format_bytes, format_timedelta, frametimes

cv2.setLogLevel(1)


class Video(File):  # noqa (PLR0904) - Too many public methods (23 > 20)
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

    def __init__(self, path: str | Path, *args, **kwargs) -> None:
        """Initialize a new Video object.

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
            return format_bytes(self.bitrate)
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
            return not cap.isOpened()
        except (OSError, SyntaxError):
            return True  # Video is corrupt
        except KeyboardInterrupt:
            sys.exit(0)

    @property
    def ffprobe(self) -> FFStream | None:
        """Return the first video stream."""
        try:
            stream = next(s for s in FFProbe(str(self.resolve())).streams if s.is_video())
            self.metadata.update({k: v for k, v in stream.__dict__.items() if "tags" not in k})
            return stream

        except StopIteration:
            if self.is_corrupt:
                raise CorruptMediaError(f"{self.absolute()} is corrupt.") from StopIteration
        except IndexError:
            if self.is_corrupt:
                raise CorruptMediaError(f"{self.absolute()} is corrupt.") from IndexError
            raise FFProbeError(
                f"FFprobe did not find any video streams for {self.path}."
            ) from IndexError
        return None

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

    def make_gif(self, scale=640, fps=24, **kwargs: Any) -> Img:
        """Convert the video to a gif using FFMPEG.

        Parameters
        -----------
            - `scale` : int, optional (default is 500)
            - `fps`   : int, optional (default is 10)
            - `output` : str, optional (default is "./output.gif")
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
            - `Img` : New `Img` object of the gif created from this video file.
        """
        output = kwargs.get("output", f'{self.parent}/{self.prefix}{".gif"}')
        output_path = Path(output)
        if output_path.exists():
            if input("Overwrite existing file? (y/n): ").lower() in {"Y", "y", "yes"}:
                output_path.unlink()
            else:
                print("Not overwriting existing file")
                return Img(output_path)
        subprocess.check_output(
            [
                "ffmpeg",
                "-i",
                f"{self.path}",
                "-vf",
                f"fps={fps},scale={scale!s}:-1:flags=lanczos",
                "-v",
                "error",
                "-loglevel",
                "quiet",
                f"{output_path}",
            ]
        )
        print(
            *[
                "ffmpeg",
                "-i",
                f"{self.path}",
                "-vf",
                f"fps={fps},scale={scale!s}:-1:flags=lanczos",
                f"{output_path}",
                "-v",
                "error",
                "-loglevel",
                "quiet",
                "-y",
            ]
        )
        # Other options: "-pix_fmt","rgb24" |
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
                    output_path,
                    frame,
                )
                saved_frames.append(Img(output_path))
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
        result = subprocess.check_call(
            f"ffmpeg -ss {start} -to {end} -i {self!s} -codec copy -v quiet -y {output_path}",
            shell=True,
        )
        return Video(output_path)

    def compress(self, **kwargs: Any) -> "Video":
        """Compress video using x265 codec with crf 18.

        Keyword Arguments:
        ----------------
        The following default ffmpeg params can be modifed by specifying them as keyword arguments

        | Flag         | Default Parameters |
        | :-------     | ------------------:|
        | -c:v         | hevc_nvenc         |
        | -crf         | 20                 |
        | -qp          | 24                 |
        | -rc          | constqp            |
        | -preset      | slow               |
        | -tune        | hq                 |
        | -v           | quiet              |
        | --output     | ./origname.mp4     |

        Examples
        --------
        ```python
        # ffmpeg -hwaccel cuda -i <input> -c:v hevc_nvenc -preset slow \
           -crf 18 -c:a copy -v quiet -y <output>
        vid.compress(output="~/Videos/compressed_video.mp4", codec="hevc_nvenc")
        ```
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
            # "-hwaccel",
            # "cuda",
            "-i",
            self.path,
            "-c:v",
            kwargs.get("codec", "libx264"),
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

    # def sha256(self) -> str:
    #     serialized_object = pickle.dumps(
    #         {
    #             "md5": self.md5_checksum(),
    #             "size": self.size,
    #         }
    #     )
    #     return hashlib.sha256(serialized_object).hexdigest()

    def __repr__(self) -> str:
        """Return a string representation of the file."""
        return f"{self.__class__.__name__}(name={self.name}, size={self.size_human})".format(
            **vars(self)
        )

    # def __hash__(self) -> int:
    #     return hash(self.sha256())
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
