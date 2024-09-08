"""fsutils - a collection of utilities for file system manipulation and data extraction."""

from .DirNode import Dir as Dir
from .FFProbe import (
    FFProbe as FFProbe,
    FFStream as FFStream,
)
from .GenericFile import File as File
from .GitObject import Git as Git
from .ImageFile import Img as Img
from .LogFile import Log as Log
from .mimecfg import FILE_TYPES as FILE_TYPES
from .ScriptFile import Exe as Exe
from .VideoFile import Video as Video

__all__ = [
    "File",
    "Img",
    "Video",
    "Log",
    "Exe",
    "Dir",
    "FFProbe",
    "Dir",
    "Git",
    "FFProbe",
    "FFStream",
]
