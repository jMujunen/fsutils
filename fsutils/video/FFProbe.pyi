"""Type annotations for FFProbe."""

class FFStream:
    """An object representation of an individual stream in a multimedia file."""

    index: int
    codec_name: str
    codec_long_name: str
    codec_tag_string: str
    codec_tag: str
    width: int
    height: int
    coded_with: int
    coded_height: int
    closed_captions: int
    has_b_frames: int
    pix_fmt: str
    level: int
    chrroma_location: str
    field_order: str
    profile: str
    refs: int
    is_avc: str
    nal_length_size: str
    id: str
    sample_aspect_ratio: str
    display_aspect_ratio: str
    r_frame_rate: str
    avg_frame_rate: str
    time_base: str
    start_pts: int
    start_time: str
    duration_ts: int
    duration: str
    bit_rate: str
    bits_per_raw_sample: str
    nb_frames: int
    extradata_size: int
    disposition: dict[str, int]
    channel_layout: str
    channels: int
    sample_rate: int
    sample_fmt: str
    nb_samples: int
    tags: dict[str, str]
    def __init__(self, index: dict) -> None:
        """Initialize the FFStream object."""

    def __repr__(self) -> str: ...
    def is_audio(self) -> bool:
        """Is this stream labelled as an audio stream?."""
    def is_video(self) -> bool:
        """Is the stream labelled as a video stream."""
    def is_subtitle(self) -> bool:
        """Is the stream labelled as a subtitle stream."""
    def is_attachment(self) -> bool:
        """Is the stream labelled as a attachment stream."""
    @property
    def frame_size(self) -> tuple[int, int] | None:
        """Return the pixel frame size as an integer tuple (width,height) if the stream is a video stream.
        Return None if it is not a video stream.
        """

    @property
    def pixel_format(self) -> str | None:
        """Return a string representing the pixel format of the video stream. e.g. yuv420p.
        Return none is it is not a video stream.
        """

    @property
    def frames(self) -> int:
        """Return the length of a video stream in frames. Return 0 if not a video stream."""

    @property
    def duration_seconds(self) -> float:
        """Return the runtime duration of the video stream as a floating point number of seconds.
        Return 0.0 if not a video stream.
        """

    @property
    def language(self) -> str | None:
        """Return language tag of stream. e.g. eng."""

    @property
    def codec(self) -> str | None:
        """Return a string representation of the stream codec."""

    @property
    def codec_description(self) -> str:
        """Return a long representation of the stream codec."""

    @property
    def frame_rate(self) -> int:
        """Return the frames per second as an integer."""

    @property
    def aspect_ratio(self) -> str | None:
        """Return the stream's display aspect ratio."""

class FFProbe:
    """FFProbe wraps the ffprobe command and pulls the data into an object form::
    metadata = FFProbe("multimedia-file.mov").
    """

    streams: list[FFStream]
    def __init__(self, filepath: str) -> None:
        """Initialize the FFProbe object.

        Parameters
        ------------
            - `path_to_video (str)` : Path to video file.
        """

    def __repr__(self) -> str: ...
