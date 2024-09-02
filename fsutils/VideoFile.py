"""Video: Represents a video file. Has methods to extract metadata like fps, aspect ratio etc."""

import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import cv2
from rich.console import Console
from rich.table import Table
from size import Size

from .exceptions import CorruptMediaError, FFProbeError
from .FFProbe import FFProbe, FFStream
from .GenericFile import File
from .ImageFile import Img


class Video(File):
    """A class representing information about a video.

    | Method | Description |
    | :---------------- | :-------------|
    | `metadata()`     | Extract video metadata |
    | `compress(output=./output.mp4)` | Compress the video using ffmpeg |
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

    def __init__(self, path: str) -> None:
        self._metadata = None
        self._info = None
        super().__init__(path)

    @property
    def metadata(self) -> dict:
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
            bitrate = round(int(self.metadata.get("bit_rate", -1)))
            return bitrate
        except ZeroDivisionError:
            if self.is_corrupt:
                print(f"\033[31m{self.basename} is corrupt!\033[0m")
            return 0

    @property
    def bitrate_human(self) -> str | None:
        """Return the bitrate in a human readable format."""
        if self.bitrate is not None and self.bitrate > 0:
            return str(Size(self.bitrate))

    @property
    def duration(self) -> int:
        return round(float(self.metadata.get("duration", 0)))

    @property
    def capture_date(self) -> datetime:
        """Return the capture date of the file."""
        capture_date = str(
            self.tags.get("creation_time") or datetime.fromtimestamp(os.path.getmtime(self.path))
        ).split(".")[0]
        return datetime.fromisoformat(capture_date)

    @property
    def codec(self) -> str | None:
        """Codec eg `H264` | `H265`"""
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
            if not cap.isOpened():
                return True  # Video is corrupt
            else:
                return False  # Video is not corrupt
        except (OSError, SyntaxError):
            return True  # Video is corrupt
        except KeyboardInterrupt:
            sys.exit(0)

    @property
    def ffprobe(self) -> FFStream | None:
        try:
            return [stream for stream in FFProbe(self.path).streams if stream.is_video()][0]
        except IndexError:
            if self.is_corrupt:
                raise CorruptMediaError(f"{self.path} is corrupt.") from IndexError
            else:
                raise FFProbeError(
                    f"FFprobe did not find any video streams for {self.path}."
                ) from IndexError

    @property
    def fps(self) -> int:
        """Return the frames per second of the video."""
        return self.ffprobe.frame_rate()

    @property
    def quality(self):  # -> float:
        return f"{round(self.num_frames / self.bitrate, 2)}"

    @property
    def num_frames(self) -> int:
        """Return the number of frames in the video."""
        return int(self.ffprobe.__dict__.get("nb_frames", -1))

    def render(self) -> None:
        """Render the video using in the shell using kitty protocols."""
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

    def make_gif(self, scale: str | int = 320, fps=24, output="./output.gif") -> Img:
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
            int : subprocess return code
        """
        output = os.path.join(self.dir_name, output) or os.path.join(
            self.dir_name, self.basename[:-4] + ".gif"
        )
        # w = scale
        # h = round(scale * 0.5625)
        # scale = f"{w}x{h}"
        # "-r",
        # str(fps),
        # "-s",
        # scale,
        subprocess.check_output(
            [
                "ffmpeg",
                "-i",
                self.path,
                # "-vf",
                # f"fps={fps},scale=-1:{str(scale)}:flags=lanczos",
                "-c:v",
                "gif",
                "-r",
                f"{fps}",
                "-s",
                f"{scale}",
                "-c:v",
                "gif",
                "-r",
                f"{fps}",
                "-s",
                f"{scale}",
                "-pix_fmt",
                "rgb8",
                "-y",
                output,
                "-v",
                "error",
            ]
        )

        return Img(output)

    def trim(self, start_: int = 0, end_: int = 100, output: str | Path | None = None) -> int:
        """Trim the video from start to end time (seconds).

        Parameters:
        ----------
            start_ : int, optional (default is 0)
            end_    : int, optional  (default is 100)
            output : str, optional (default is current working directory)

        Returns:
        --------
        Returns:
            int : subprocess return code
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
            `output` : Save compressed video to this path

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

    # NOTE:  Untested
    def extract_audio(self, output_path: str | None = None) -> int:
        return subprocess.call(
            [
                "ffmpeg",
                "-i",
                f"{self.path}",
                "-vn",
                "-y",
                f"{os.path.splitext(self.path)[0]}_audio.wav",
            ]
        )

    # NOTE:  Untested
    def extract_subtitle(self, output_path: str | None = None) -> int:
        return subprocess.call(
            f"ffmpeg -i {self.path} -map s -c copy {os.path.splitext(self.path)[0]}_subtitle.srt",
            shell=True,
        )

    @property
    def md5_checksum(self) -> str:
        """Return the MD5 checksum of the video file."""
        with open(self.path, "rb") as f:
            return hashlib.md5(f.read()).hexdigest()

    # NOTE:  Untested
    def extract_frames(self, output_path: str | None = None) -> int:
        # [ ] - WIP
        return subprocess.call(f"ffmpeg  -i {self.path}  image%03d.jpg", shell=True)

    def __repr__(self) -> str:
        """Return a string representation of the file."""
        return f"{self.__class__.__name__}(size={self.size_human}, bitrate={self.bitrate_human}, codec={self.codec},)".format(
            **vars(self)
        )

    def __hash__(self) -> int:
        return hash((self.bitrate, self.duration, self.codec, self.fps, self.md5_checksum))

    def __format__(self, format_spec: str, /) -> str:
        """Return a formatted string representation of the file."""
        name = self.basename
        iterations = 0
        while len(name) > 20 and iterations < 5:  # Protection from infinite loop
            if "-" in name:
                name = name.split("-")[-1]
            else:
                name = ".".join([name.split(".")[0], name.split(".")[-1]])
            iterations += 1
        return f"{name.strip():<25} | {self.num_frames:<10} | {self.bitrate_human:<10} | {self.size_human:<10} | {self.codec:<10} | {self.duration:<10} | {self.fps:<10} | {str(self.dimensions):<10}"

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


class FFMpegManager:
    def __init__(self, movie: Video) -> None:
        self.file = movie

    def __enter__(self) -> None:
        pass

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        if exc_type is not None:
            try:
                os.remove(self.file.path)
            except OSError:
                pass
            return True
        else:
            return False


if __name__ == "__main__":
    from . import Dir

    videos = Dir("/mnt/ssd/OBS/muru/PUBG/_PLAYERUNKNOWN'S BATTLEGROUNDS/").videos[:-2]
    for vid in videos:
        compressed = vid.compress()
