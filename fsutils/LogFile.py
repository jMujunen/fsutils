"""This module exposes the Log class as a parent of File"""

import pandas as pd
import re
from io import StringIO
from typing import Any

from .GenericFile import File

DIGIT_REGEX = re.compile(r"(\d+(\.\d+)?)")


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

    sanatized = False

    def __init__(self, path, spec="csv", encoding="iso-8859-1"):
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
        """Get the columns of the log file as a list"""
        try:
            first_line = self.head()[0]
            return first_line.split(self.spec)
        except IndexError:
            return []

    def to_df(self) -> pd.DataFrame:
        """Convert the log file into a pandas DataFrame."""
        import pandas as pd

        return pd.read_csv(StringIO("\n".join(self.sanitize())), delimiter=self.spec)

    def sanitize(self) -> list[str]:
        """Sanitize the log file by removing any empty lines, spaces,
        special charactesrs, and trailing delimiters. Also remove the last 2 lines
        """
        # Skip sanitizing if already done
        if self.sanatized:
            return self.content
        num_lines = len(self)
        sanatized_header = [col.strip() for col in self.columns]

        HEADER_SANATIZER = re.compile(
            r"(GPU2.\w+\(.*\)|NaN|N\/A|Fan2|°|Â|\*|,,+|\s\[[^\s]+\]|\"|\+|\s\[..TDP\]|\s\[\]|\s\([^\s]\))"
        )

        sanatized_content = [
            HEADER_SANATIZER.sub("", row) for i, row in enumerate(self) if i < num_lines - 2
        ]

        self._content = sanatized_content
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

    def compare(self, other: "Log") -> None:
        """Compare the statistics of this log file with another.

        Prints a table comparing each column's mean values."""

        def round_values(val: float | int) -> float:
            try:
                val = float(val)
                if val < 5:
                    return round(val, 3)
                elif 5 <= val < 15:
                    return round(val, 2)
                else:
                    return int(val)
            except ValueError as e:
                print(f"\033[31m Error rounding value: {e}\033[0m")
                return val

        def compare_values(num1: float | int, num2: float | int) -> tuple:
            num1 = round_values(num1)
            num2 = round_values(num2)
            if num1 == num2:
                return (f"{num1}", str(num1))
            elif num1 > num2:
                return (f"\033[32m{num1}\033[0m", f"\033[31m+{str(num1 - num2)}\033[0m")
            else:
                return (f"\033[31m{num1}\033[0m", f"\033[32m+{str(num2 - num1)}\033[0m")

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
