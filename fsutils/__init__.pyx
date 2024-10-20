"""fsutils - a collection of utilities for file system manipulation and data extraction."""

from . import (
    DirNode as DirNode
)
from . import (
    FFProbe as FFProbe,
)
from . import GenericFile as GenericFile
from . import GitObject as GitObject
from . import ImageFile as ImageFile
from . import (
    LogFile as LogFile,
)

# from .LogFile.Presets import Presets as Presets
from . import (
    mimecfg as mimecfg,
)
from . import VideoFile as VideoFile

__all__ = [
    "GenericFile.File",
    "ImageFile.Img",
    "VideoFile.Video",
    "LogFile.Log",
    "Dir",
    "FFProbe",
    "Dir",
    "Git",
    "FFProbe",
    "FFProbe.FFStream",
    "obj",
    "mimecfg.FILE_TYPES",
    "IGNORED_DIRS",
    "Presets",
]
