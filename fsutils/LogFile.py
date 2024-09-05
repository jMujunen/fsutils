"""This module exposes the Log class as a parent of File."""

import pandas as pd
import re
from dataclasses import dataclass, field
from typing import Any

from .GenericFile import File

DIGIT_REGEX = re.compile(r"(\d+(\.\d+)?)")


@dataclass
class LogEntry(File):
    """A class to represent a log entry."""

    path: str = field(default_factory=lambda: "")
    sep: str = field(default=",")

    encoding: str = field(default="iso-8859-1")
    df: pd.DataFrame = field(default_factory=pd.DataFrame, repr=False)

    def __post_init__(self):
        """Initialize a LogEntry object."""
        super().__init__(path=self.path, encoding=self.encoding)
        self.df = pd.read_csv(self.path, sep=self.sep, encoding=self.encoding, engine="python")
        self.columns = list(self.df.columns)
        self.describe = self.df.describe()
        self.min = self.df.min()
        self.max = self.df.max()


class Log(File):
    """
    A class to represent a hwlog file.

    Attributes:
    ----------
        path (str): The absolute path to the file.
        spec (str, optional): The delimiter used in the log file. Defaults to 'csv'.
        encoding (str, optional): The encoding scheme used in the log file. Defaults to 'iso-8859-1'.

    Methods:
    ----------
        header (str): Get the header of the log file.
        columns (list): Get the columns of the log file.
        footer (str): Get the footer of the log file.

    """

    def __init__(self, path: str, spec="csv", encoding="iso-8859-1"):
        """Initialize a Log object."""
        specs = {"csv": ",", "tsv": "\t", "custom": ", "}
        if spec not in specs:
            raise ValueError(f"Unsupported spec: {spec}. Supported specs are {list(specs.keys())}.")
        self.spec = specs[spec]
        super().__init__(path, encoding)

    @property
    def header(self) -> str:
        """Get the header of the log file."""
        try:
            return self.head()[0].strip().strip(self.spec)
        except IndexError:
            return ""

    @property
    def columns(self) -> list[str]:
        """Get the columns of the log file as a list."""
        try:
            first_line = self.head()[0]
            return first_line.split(self.spec)
        except IndexError:
            return []

    def sanitize(self) -> list[str]:
        """Sanitize the log file.

        Remove any empty lines, spaces, special characters, and trailing delimiters.
        Also remove the last 2 lines.
        """
        # Skip sanitizing if already done
        num_lines = len(self)
        lines = [col.strip() for col in self.columns]

        HEADER_SANATIZER = re.compile(
            r"(GPU2.\w+\(.*\)|NaN|N\/A|Fan2|°|Â|\*|,,+|\s\[[^\s]+\]|\"|\+|\s\[..TDP\]|\s\[\]|\s\([^\s]\))"
        )

        sanitized_content = [
            HEADER_SANATIZER.sub("", row) for i, row in enumerate(self) if i < num_lines - 2
        ]

        self._content = sanitized_content
        self.sanatized = True
        return self._content

    @property
    def stats(self) -> Any:
        """Calculate basic statistical information for the data in a DataFrame."""
        try:
            df = pd.read_csv(self.path)
        except UnicodeDecodeError:
            df = self.to_df()
        return df.mean()

    @property
    def content(self) -> list[Any]:
        return [line.strip() for line in super().content if line]

    def compare(self, other: "Log") -> None:
        """Compare the statistics of this log file with another.

        Prints a table comparing each column's mean values."""

        def round_values(val: float | int) -> float:
            try:
                val = float(val)
                if val < 5:
                    return round(val, 3)
                if 5 <= val < 15:
                    return round(val, 2)
                return int(val)
            except ValueError as e:
                print(f"\033[31m Error rounding value: {e}\033[0m")
                return val

        def compare_values(num1: float | int, num2: float | int) -> tuple:
            num1 = round_values(num1)
            num2 = round_values(num2)
            if num1 == num2:
                return (f"{num1}", str(num1))
            if num1 > num2:
                return (f"\033[32m{num1}\033[0m", f"\033[31m+{num1 - num2!s}\033[0m")
            return (f"\033[31m{num1}\033[0m", f"\033[32m+{num2 - num1!s}\033[0m")

        print("{:<20} {:>15} {:>20}".format("Sensor", self.basename, other.basename))
        for k in set(self.stats.keys()).intersection(other.stats.keys()):
            num1, num2 = compare_values(self.stats[k], other.stats[k])
            print(f"{k:<32} {num1:<15} {num2:>20}")

    #  FIXME : Account for differences in columns. Currently, differences in columns output the following:
    #     """ 12V                              + 44                  11.94
    #         Vcore                            1.287               + 1.301
    #         VIN3                             + 55                  1.315
    #         GPU_Temperature                  + 70                     55
    #         GPU_Clock                        + 2575                 1964
    #         Frame_Time                       4.07                 + 8.73
    #         GPU_Busy                         + 58                  4.749 """

    def save(self) -> None:
        # FIXME : Create a backup first
        """Save the (updated) content to the log file (overwrites original content)."""
        with open(self.path, "w", encoding=self.encoding) as f:
            f.write("\n".join(self._content))
