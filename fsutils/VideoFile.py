"""Video: Represents a video file. Has methods to extract metadata like fps, aspect ratio etc."""

from datetime import datetime
import subprocess
import os
import json
import cv2
import sys
from dataclasses import dataclass
from pathlib import Path
from .GenericFile import File


@dataclass
class Video(File):
    """
    A class representing information about a video.

    Attributes:
    ----------
        path (str): The absolute path to the file.

    Methods:
    ----------
        metadata (dict): Extract metadata from the video including duration,
                        dimensions, fps, and aspect ratio.
        bitrate (int): Extract the bitrate of the video from the ffprobe output.
        is_corrupt (bool): Check integrity of the video.

    """

    def __init__(self, path: str):
        self._metadata = None
        super().__init__(path)

    @property
    def metadata(self):
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
            except subprocess.CalledProcessError as e:
                print(f"Failed to run ffprobe on {self.path}.", file=sys.stderr)
                self._metadata = {}
        return self._metadata

    @property
    def tags(self):
        return self.metadata.get("tags", {}) if self.metadata else {}

    @property
    def bitrate(self) -> int:
        """Extract the bitrate with ffprobe.

        Returns:
        ----------
            int: The bitrate of the video in bits per second.
        """
        return self.metadata.get("bit_rate", -1)

    @property
    def duration(self) -> float:
        return self.metadata.get("duration", 0)

    @property
    def capture_date(self) -> datetime | None:
        return self.tags.get("creation_time")

    # @property
    # def capture_date(self):
    #     if not self._metadata:
    #         self._metadata =

    @property
    def is_corrupt(self) -> bool:
        """
        Check if the video is corrupt.

        Returns:
        ----------
            bool: True if the video is corrupt, False otherwise.
        """
        try:
            cap = cv2.VideoCapture(self.path)
            if not cap.isOpened():
                return True  # Video is corrupt
            else:
                return False  # Video is not corrupt
        except (IOError, SyntaxError):
            return True  # Video is corrupt
        except KeyboardInterrupt:
            sys.exit(0)

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

    def make_gif(self, scale=500, fps=24, output="./output.gif") -> int:
        """Convert the video to a gif using FFMPEG.

        Parameters:
        -----------
            scale : int, optional (default is 500)
            fps   : int, optional (default is 10)
            **kwargs : dict, define output path here if nessacary

        Returns:
        --------
            int : subprocess return code
        """
        output = output or os.path.join(self.dir_name, self.basename[:-4] + ".gif")
        return subprocess.call(
            [
                "ffmpeg",
                "-i",
                f"{self.path}",
                "-vf",
                f"scale=-1:{str(scale)}:flags=lanczos",
                "-r",
                f"{str(fps)}",
                f"{output}",
                "-loglevel",
                "quiet",
            ],
        )

    def trim(self, start_: int = 0, end_: int = 100, output: str | Path | None = None) -> int:
        """Trim the video from start to end time (seconds).

        Parameters:
        ----------
            start_ : int, optional (default is 0)
            end_    : int, optional  (default is 100)
            output : str, optional (default is current working directory)

        Returns:
        --------
            int : subprocess return code
        """

        output_path = output if output else self.path[:-4] + f"_trimmed.{self.extension}"
        return subprocess.call(
            f"ffmpeg -ss mm:ss -to mm2:ss2 -i {self.path} -codec copy {output_path}"
        )

    def compress(self, output: str | None | Path = None) -> int:
        output_path = (
            output if output is not None else self.path[:-4] + f"_compressed.{self.extension}"
        )
        result = subprocess.run(
            f'ffmpeg -i "{self.path}" -c:v hevc_nvenc -crf 20 -qp 20 "{output_path}"',
            shell=True,
            capture_output=True,
            text=True,
        )
        return result.returncode

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

    def extract_subtitle(self, output_path: str | None = None) -> int:
        return subprocess.call(
            f"ffmpeg -i {self.path} -map s -c copy {os.path.splitext(self.path)[0]}_subtitle.srt",
            shell=True,
        )

    def extract_frames(self, output_path: str | None = None) -> int:
        # [ ] - WIP
        return subprocess.call(f"ffmpeg  -i {self.path}  image%03d.jpg", shell=True)

    def info(self):
        result = subprocess.run(
            f'ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "{self.path}"',
            shell=True,
            capture_output=True,
            text=True,
        )
        return float(result.stdout)
