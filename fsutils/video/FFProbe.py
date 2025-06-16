"""Python wrapper for ffprobe command line tool. ffprobe must exist in the path."""

import json
import re
import subprocess
from dataclasses import dataclass, field

from pydantic import BaseModel, Field

from fsutils.utils.Exceptions import FFProbeError

tags_key_sanitizer = re.compile(r"com.(apple.)?")


class DotDict(dict):
    """A dictionary subclass that supports dot notation for nested keys.

    Example:
    >>> d = DotDict({"a": {"b": {"c": 1}}})
    >>> print(d.a.b.c)  # Outputs: 1

    >>> d.x = {"y": {"z": 3}}
    >>> print(d.x.y.z)  # Outputs: 3

    >>> d = DotDict({"a.b.c": 5, "x.y": 10})
    >>> print(d.a.b.c)  # Outputs: 5
    >>> print(d.x.y)  # Outputs: 10
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._flatten_dict()

    def _flatten_dict(self):
        """Recursively convert nested dictionaries into DotDict instances."""
        for key in list(self.keys()):
            value = self.pop(key)
            self._process_key(key, value)

    def _process_key(self, key, value):
        """Process a key-value pair, converting nested dicts and handling dotted keys."""
        if "." in key:
            self._split_dot_key(key, value)
        else:
            if isinstance(value, dict):
                value = DotDict(value)
            self[key] = value

    def _split_dot_key(self, key, value):
        """Split a dotted key into nested structure and assign the value."""
        parts = key.split(".")
        current = self
        for part in parts[:-1]:
            if part not in current or not isinstance(current[part], dict):
                current[part] = DotDict()
            current = current[part]
        current[parts[-1]] = value

    def __getattr__(self, key):
        if key in self:
            return self[key]
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{key}'")

    def __setattr__(self, key, value):
        if isinstance(value, dict) and not isinstance(value, DotDict):
            value = DotDict(value)
        self[key] = value

    def __delattr__(self, key):
        if key in self:
            del self[key]
        else:
            raise AttributeError(
                f"'{type(self).__name__}' object has no attribute '{key}'"
            )

    def __dir__(self):
        return list(self.keys()) + super().__dir__()  # pyright: ignore[reportOperatorIssue]


class Tags:
    def __init__(self, **kwargs):
        """Initialize the Tags object."""
        for k, v in kwargs.items():
            if k in {"major_brand", "minor_version", "compatible_brands", "encoder"}:
                continue
            key = k.replace("com.", "")
            if "." in key:
                self._split_dot_key(key, v)
            else:
                setattr(self, key, v)
                self.__dict__[key] = v

    def __repr__(self) -> str:
        """Return a string representation of the Tags object."""
        return f"Tags({self.__dict__})"

    def _split_dot_key(self, key, value):
        """Split a dotted key into nested structure and assign the value."""
        parts = key.split(".")
        current = self
        for part in parts[:-1]:
            if part not in current or not isinstance(current[part], dict):
                current[part] = DotDict()
            current = current[part]
        current[parts[-1]] = value

    def __getitem__(self, key):
        return self.__dict__[key]

    def __setitem__(self, key, value):
        self.__dict__[key] = value

    def __iter__(self):
        return iter(self.__dict__)

    def __dir__(self):
        return list(self.__dict__.keys()) + super().__dir__()  # pyright: ignore[reportOperatorIssue]


class Stream(BaseModel):
    codec_name: str = Field(kw_only=True, default="")
    codec_type: str = Field(kw_only=True, default="")
    duration: float | None = None
    bit_rate: int | None = None
    sample_rate: int | None = None

    def is_video(self) -> bool:
        """Check if the stream is a video."""
        return self.codec_type == "video"

    def is_audio(self) -> bool:
        """Check if the stream is an audio."""
        return self.codec_type == "audio"

    def is_subtitle(self) -> bool:
        """Check if the stream is a subtitle."""
        return self.codec_type == "subtitle"

    def is_data(self) -> bool:
        """Check if the stream is a data."""
        return self.codec_type == "data"


class VideoStream(Stream):
    width: int = Field(kw_only=True, default=0)
    height: int = Field(kw_only=True, default=0)
    codec_name: str = Field(kw_only=True, default="")
    codec_type: str = Field(kw_only=True, default="")
    pix_fmt: str = Field(kw_only=True, default="")
    r_frame_rate: str | None = None
    avg_frame_rate: str | None = None
    duration: float | None = None

    profile: str | None = None
    level: int | None = None
    color_range: str | None = None
    color_space: str | None = None
    color_transfer: str | None = None
    color_primaries: str | None = None
    chroma_location: str | None = None
    field_order: str | None = None
    time_base: str | None = None
    start_time: float | None = None
    nb_frames: int | None = None


class AudioStream(Stream):
    title: str | None = None
    artist: str | None = None
    album: str | None = None
    sample_rate: int | None = None
    channels: int | None = None
    channel_layout: str | None = None


@dataclass
class FFProbe:
    """FFProbe wraps the ffprobe command and pulls the data into an object form::
    metadata = FFProbe("multimedia-file.mov").
    """

    path: str
    streams: list[Stream] = field(default_factory=list)
    # videostream: VideoStream = field(default_factory=VideoStream)
    # audiostream: AudioStream = field(default_factory=AudioStream)
    tags: Tags = field(default_factory=Tags)

    def __post_init__(self) -> None:
        """Initialize the FFProbe object."""
        cmd = 'ffprobe -v error -show_streams -show_format -output_format json file:"{}"'

        result = subprocess.getoutput(cmd.format(str(self.path)))
        data = json.loads(result)

        streams = data.get("streams", [])
        tags = data.get("format", {}).get("tags", {})
        self.tags = Tags(**tags)
        if not streams:
            raise FFProbeError(f"No streams found in file {self.path}")

        for stream in streams:
            if stream["codec_type"] == "audio":
                self.streams.append(AudioStream(**{**stream, **tags}))
            elif stream["codec_type"] == "video":
                self.streams.append(VideoStream(**stream))

        # for stream in streams:
        # FFStream.__init__(self, stream)

    def __len__(self):
        """Return the number of streams."""
        return len(self.streams)
