"""Python wrapper for ffprobe command line tool. ffprobe must exist in the path."""

import functools
import operator
import os
import pipes
import platform
import re
import subprocess
from pathlib import Path

# from ..fsutils import Video
from Exceptions import CorruptMediaError, FFProbeError


class FFProbe:
    """FFProbe wraps the ffprobe command and pulls the data into an object form::
    metadata = FFProbe("multimedia-file.mov").
    """

    streams: list["FFStream"]

    def __init__(self, filepath: str) -> None:
        """Initialize the FFProbe object.

        Parameters
        ------------
            - `path_to_video (str)` : Path to video file.
        """
        self.file = Path(filepath)

        try:
            with open(os.devnull, "w") as tempf:
                subprocess.check_call(["ffprobe", "-h"], stdout=tempf, stderr=tempf)
        except FileNotFoundError:
            raise OSError("ffprobe not found.") from FileNotFoundError
        if self.file.is_file() or str(self.file.absolute()).startswith("http"):
            if platform.system() == "Windows":
                cmd = ["ffprobe", "-show_streams", f"{self.file}"]
            else:
                cmd = ["ffprobe -show_streams " + pipes.quote(f"{self.file}")]

            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)

            stream = False
            ignoreLine = False
            self.streams = []
            self.video = []
            self.audio = []
            self.subtitle = []
            self.attachment = []

            for line in iter(proc.stdout.readline, b""):
                line = line.decode("UTF-8", "ignore")
                if "[STREAM]" in line:
                    stream = True
                    ignoreLine = False
                    data_lines = []
                elif "[/STREAM]" in line and stream:
                    stream = False
                    ignoreLine = False
                    self.streams.append(FFStream(data_lines))
                elif stream:
                    if "[SIDE_DATA]" in line:
                        ignoreLine = True
                    elif "[/SIDE_DATA]" in line:
                        ignoreLine = False
                    elif not ignoreLine:
                        data_lines.append(line)

            self.metadata = {}
            is_metadata = False
            stream_metadata_met = False

            for line in iter(proc.stderr.readline, b""):
                line = line.decode("UTF-8", "ignore")

                if "Metadata:" in line and not stream_metadata_met:
                    is_metadata = True
                elif "Stream #" in line:
                    is_metadata = False
                    stream_metadata_met = True
                elif is_metadata:
                    splits = line.split(",")
                    for s in splits:
                        m = re.search(r"(\w+)\s*:\s*(.*)$", s)
                        if m is not None:
                            # print(m.groups())
                            self.metadata[m.groups()[0]] = m.groups()[1].strip()

                if "[STREAM]" in line:
                    stream = True
                    data_lines = []
                elif "[/STREAM]" in line and stream:
                    stream = False
                    self.streams.append(FFStream(data_lines))
                elif stream:
                    data_lines.append(line)

            proc.stdout.close()
            proc.stderr.close()

            for stream in self.streams:
                if stream.is_audio():
                    self.audio.append(stream)
                elif stream.is_video():
                    self.video.append(stream)
                elif stream.is_subtitle():
                    self.subtitle.append(stream)
                elif stream.is_attachment():
                    self.attachment.append(stream)
        elif not self.file.exists():
            raise FileNotFoundError(f"File does not exist: {self.file}")
        elif self.file.is_dir():
            raise IsADirectoryError("Given path is a directory, not a file.")
        else:
            raise CorruptMediaError(f"{self.file} is corrupt")

    def __repr__(self) -> str:
        return "FFprobe(metadata={metadata}, video={video}, audio={audio})".format(**vars(self))


class FFStream:
    """An object representation of an individual stream in a multimedia file."""

    def __init__(self, data_lines):
        for line in data_lines:
            self.__dict__.update({key: value for key, value, *_ in [line.strip().split("=")]})

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
            template = (
                "Stream: #{index} [{codec_type}] {codec_long_name}, {framerate}, ({width}x{height})"
            )

        elif self.is_audio():
            template = (
                "Stream: #{index} [{codec_type}] {codec_long_name}, channels: {channels} ({channel_layout}), "
                "{sample_rate}Hz "
            )

        elif self.is_subtitle() or self.is_attachment():
            template = "Stream: #{index} [{codec_type}] {codec_long_name}"

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
