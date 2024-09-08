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


class Log(File, LogMetaData):
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
