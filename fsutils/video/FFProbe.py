"""Python wrapper for ffprobe command line tool. ffprobe must exist in the path."""

import functools
import json
import operator
import subprocess
from pathlib import Path

from fsutils.utils.Exceptions import CorruptMediaError, FFProbeError


class FFProbe:
    """FFProbe wraps the ffprobe command and pulls the data into an object form::
    metadata = FFProbe("multimedia-file.mov").
    """

    def __init__(self, filepath: str) -> None:
        """Initialize the FFProbe object.

        Parameters
        ------------
            - `path_to_video (str)` : Path to video file.
        """
        self.streams = []
        cmd = "ffprobe -print_format json -show_streams {path} -v quiet"
        data = json.loads(subprocess.getoutput(cmd.format(path=filepath))).get("streams", [])

        if not data:
            raise FFProbeError(f"No streams found in file {filepath}")

        for stream in data:
            self.streams.append(FFStream(stream))

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(streams={self.streams})"


class FFStream:
    """An object representation of an individual stream in a multimedia file."""

    def __init__(self, index: dict) -> None:
        """Initialize the FFStream object."""
        self.__dict__.update(index)
        try:
            self.__dict__["framerate"] = round(
                functools.reduce(
                    operator.truediv,
                    map(int, self.__dict__.get("avg_frame_rate", "").split("/")),
                )
            )

        except ValueError:
            self.__dict__["framerate"] = None
        except ZeroDivisionError:
            self.__dict__["framerate"] = 0

    def __repr__(self) -> str:
        if self.is_video():
            template = "Stream[{codec_type}]({codec_name}, {framerate}, ({width}x{height}))"

        elif self.is_audio():
            template = (
                "Stream[{codec_type}]({codec_name}, channels: {channels} ({channel_layout}), "
                "{sample_rate}Hz)"
            )

        elif self.is_subtitle() or self.is_attachment():
            template = "Stream: #{index} [{codec_type}] {codec_name}"

        else:
            template = ""

        return template.format(**self.__dict__)

    def is_audio(self) -> bool:
        """Is this stream labelled as an audio stream?."""
        return self.__dict__.get("codec_type", None) == "audio"

    def is_video(self) -> bool:
        """Is the stream labelled as a video stream."""
        return self.__dict__.get("codec_type", None) == "video"

    def is_subtitle(self) -> bool:
        """Is the stream labelled as a subtitle stream."""
        return self.__dict__.get("codec_type", None) == "subtitle"

    def is_attachment(self) -> bool:
        """Is the stream labelled as a attachment stream."""
        return self.__dict__.get("codec_type", None) == "attachment"

    def frame_size(self) -> tuple[int, int] | None:
        """Return the pixel frame size as an integer tuple (width,height) if the stream is a video stream.
        Return None if it is not a video stream.
        """
        size = None
        if self.is_video():
            width = self.__dict__["width"]
            height = self.__dict__["height"]

            if width and height:
                try:
                    size = (int(width), int(height))
                except ValueError:
                    raise FFProbeError(f"None integer size {width}:{height}") from ValueError
        else:
            return None

        return size

    def pixel_format(self) -> str | None:
        """Return a string representing the pixel format of the video stream. e.g. yuv420p.
        Return none is it is not a video stream.
        """
        return self.__dict__.get("pix_fmt", None)

    def frames(self) -> int:
        """Return the length of a video stream in frames. Return 0 if not a video stream."""
        if self.is_video() or self.is_audio():
            if self.__dict__.get("nb_frames", "") != "N/A":
                try:
                    frame_count = int(self.__dict__.get("nb_frames", ""))
                except ValueError:
                    raise FFProbeError("None integer frame count") from ValueError
            else:
                # When N/A is returned, set frame_count to 0 too
                frame_count = 0
        else:
            frame_count = 0

        return frame_count

    def duration_seconds(self) -> float:
        """Return the runtime duration of the video stream as a floating point number of seconds.
        Return 0.0 if not a video stream.
        """
        if self.is_video() or self.is_audio():
            try:
                duration = float(self.__dict__.get("duration", ""))
            except ValueError:
                raise FFProbeError("None numeric duration") from ValueError
        else:
            duration = 0.0

        return duration

    def language(self) -> str | None:
        """Return language tag of stream. e.g. eng."""
        return self.__dict__.get("TAG:language", None)

    def codec(self) -> str | None:
        """Return a string representation of the stream codec."""
        return self.__dict__.get("codec_name", None)

    def codec_description(self) -> str:
        """Return a long representation of the stream codec."""
        return self.__dict__.get("codec_long_name", None)

    def codec_tag(self) -> str | None:
        """Return a short representative tag of the stream codec."""
        return self.__dict__.get("codec_tag_string", None)

    def bit_rate(self) -> int | None:
        """Return bit_rate as an integer in bps."""
        try:
            return int(self.__dict__.get("bit_rate", ""))
        except ValueError:
            raise FFProbeError("None integer bit_rate") from ValueError

    def frame_rate(self) -> int:
        """Return the frames per second as an integer."""
        try:
            return int(self.__dict__.get("framerate", ""))
        except ValueError:
            try:
                return int(self.__dict__.get("r_frame_rate", "").split("/")[0])
            except Exception:
                return 0

    def aspect_ratio(self) -> str | None:
        """Return the stream's display aspect ratio."""
        return self.__dict__.get("display_aspect_ratio", None)
