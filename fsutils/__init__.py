"""fsutils - a collection of utilities for file system manipulation and data extraction."""

from .DirNode import (
    Dir as Dir,
    obj as obj,
)
from .FFProbe import (
    FFProbe as FFProbe,
    FFStream as FFStream,
)
from .GenericFile import File as File
from .GitObject import Git as Git
from .ImageFile import Img as Img
from .LogFile.Log import Log as Log
from .LogFile.Presets import Presets as Presets
from .mimecfg import (
    FILE_TYPES as FILE_TYPES,
    IGNORED_DIRS as IGNORED_DIRS,
)
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
    "obj",
    "FILE_TYPES",
    "IGNORED_DIRS",
    "Presets",
]
