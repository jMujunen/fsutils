# from pydantic import BaseModel, Field, dataclasses

from fsutils.file import Base
from fsutils.utils.tools import format_bytes
from fsutils.video.FFProbe import FFProbe, Stream, Tags


class Audio(Base):
    def __init__(self, path: str) -> None:
        """Initialize a new Audio object.

        Paramaters:
        -------------
            - `path (str)` : The absolute path to the video file.

        """
        super().__init__(path)
        _ = self.metadata

    @property
    def metadata(self) -> Stream:
        """Extract the metadata of the video."""
        probe = FFProbe(self.path)
        for stream in probe.streams:
            if stream.is_audio():
                for k, v in stream.__dict__.items():
                    setattr(self, k, v)
                return stream
        raise ValueError(f"No video stream found in {self.name}")
