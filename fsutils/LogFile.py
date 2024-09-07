"""This module exposes the Log class as a parent of File."""

import pandas as pd
import re
from dataclasses import dataclass, field

from .GenericFile import File

DIGIT_REGEX = re.compile(r"(\d+(\.\d+)?)")


@dataclass
class Log(File):
    """A class to represent a log entry."""

    path: str = field(default_factory=str, repr=False)
    sep: str = field(default=",")
    encoding: str = field(default="iso-8859-1")
    df: pd.DataFrame = field(default_factory=pd.DataFrame, repr=False)

    def __post_init__(self):
        """Initialize a LogEntry object."""
        super().__init__(path=self.path, encoding=self.encoding)

    def to_df(self) -> pd.DataFrame:
        self.df = pd.read_csv(self.path, sep=self.sep, encoding=self.encoding, engine="python")
        self.columns = list(self.df.columns)
        self.describe = self.df.describe()
        self.min = self.df.min()
        self.max = self.df.max()

        return self.df
