"""Video: Represents a video file. Has methods to extract metadata like fps, aspect ratio etc."""

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

import cv2
from size import Converter

from .ffprobe import FFProbe, FFStream
from .GenericFile import File


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

    def __init__(self, path: str) -> None:
        self._metadata = None
        self._info = None
        super().__init__(path)

    @property
    def metadata(self) -> Dict:
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
    def tags(self) -> Optional[Dict]:
        return self.metadata.get("tags", {}) if self.metadata else {}

    @property
    def bitrate(self) -> Optional[int]:
        """Extract the bitrate/s with ffprobe."""
        try:
            bitrate = round(int(self.metadata.get("bit_rate", -1)) / self.duration)
            return bitrate
        except ZeroDivisionError:
            if self.is_corrupt:
                print(f"\033[31m{self.basename} is corrupt!\033[0m")
            return 0

    @property
    def bitrate_human(self) -> Optional[str]:
        """Return the bitrate in a human readable format."""
        if self.bitrate is not None and self.bitrate > 0:
            return str(Converter(self.bitrate))

    @property
    def duration(self) -> int:
        return round(float(self.metadata.get("duration", 0)))

    @property
    def capture_date(self) -> datetime:
        capture_date = str(
            self.tags.get("creation_time") or datetime.fromtimestamp(os.path.getmtime(self.path))
        ).split(".")[0]
        return datetime.fromisoformat(capture_date)

    @property
    def info(self) -> FFStream | None:
        if self._info is None:
            for stream in FFProbe(self.path).streams:
                if stream.is_video():
                    self._info = stream
        return self._info

    @property
    def codec(self) -> str | None:
        return self.info.codec() if self.info else None

    @property
    def dimentions(self) -> tuple[int, int] | None:
        return self.info.frame_size() if self.info else None

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
        # TODO : Return out output gif as an object
        # [ ] Add support for more options like duration of gif and color palette.
        """Convert the video to a gif using FFMPEG.

        Parameters:
        -----------
            scale : int, optional (default is 500)
            fps   : int, optional (default is 10)
            output_path: str, optional (default is "./output.gif")

            Breakdown:
            * FPS: Deault is 24 but the for smaller file sizes, try 6-10
            * SCALE: is the width of the output gif in pixels.
                - 500-1000 = high quality but larger file size.
                - 100-500   = medium quality and smaller file size.
                - 10-100    = low quality and smaller file size.

            * The default `fps | scale` of `24 | 500` means a decent quality gif.
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
            ]
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

    def compress(self, output=None) -> int:
        file_path = f"./{self.basename[:-4]}_compressed_hevc.mp4"
        if output is not None:
            file_path = output
        # output_path = f"{output_dir}/{self.basename}"
        if os.path.exists(file_path):
            other = Video(file_path)
            if not other.is_corrupt:
                pass
        result = subprocess.run(
            f'ffmpeg -i "{self.path}" -c:v hevc_nvenc -crf 16 -qp 18 "{file_path}"',
            # f'ffmpeg -i "{self.path}" -c:v h264_nvenc -crf 18 -qp 28 "{file_path}"',
            shell=True,
            capture_output=True,
            text=True,
        )
        print(result.stderr, result.stdout)
        return result.returncode

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

    # NOTE:  Untested
    def extract_frames(self, output_path: str | None = None) -> int:
        # [ ] - WIP
        return subprocess.call(f"ffmpeg  -i {self.path}  image%03d.jpg", shell=True)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(size={self.size}, path={self.path}, basename={self.basename}, extension={self.extension}, bitrate={self.bitrate}, duration={self.duration}, codec={self.codec}, capture_date={self.capture_date}, dimensions={self.dimentions}, info={self.info}".format(
            **vars(self)
        )

    # def __repr__(self) -> str:
    #     return super().__repr__()


# Run as script
if __name__ == "__main__":
    path = sys.argv[1] or "~/mnt/ssd/OBS/Joona/PUBG/"
    vid = Video(path)
