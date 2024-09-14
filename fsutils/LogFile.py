"""This module exposes the Log class as a parent of File."""

import pandas as pd
import re
from dataclasses import dataclass, field

from .GenericFile import File

DIGIT_REGEX = re.compile(r"(\d+(\.\d+)?)")


@dataclass
class LogMetaData:
    """A class to represent a log entry."""

    path: str = field(default_factory=str, repr=False)
    sep: str = field(default=",")
    encoding: str = field(default="iso-8859-1")

    df: pd.DataFrame = field(default_factory=pd.DataFrame, repr=False)


class Log(LogMetaData, File):
    """A class to represent a log file."""

    def __init__(self, path: str, sep: str = ",", encoding: str = "iso-8859-1"):
        """Initialize the File and Log classes with the given parameters."""
        File.__init__(self, path, encoding=encoding)
        LogMetaData.__init__(self, path, sep, encoding)

    def parse(self) -> pd.DataFrame:
        """Parse the log file into a DataFrame."""
        self.df = pd.read_csv(
            self.path,
            sep=self.sep,
            encoding=self.encoding,
            engine="python",
        )
        return self.df

    def __hash__(self):
        """Return a hash of the log file."""
        return hash((type(self), self.encoding, self.md5_checksum()))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, type(self)):
            raise TypeError("Can only compare instances of the same class")

        return self.path == other.path and self.sep == other.sep and self.encoding == other.encoding

    def __ne__(self, other: object) -> bool:
        """Check if two instances of the class are not equal."""
        return not (self == other)
