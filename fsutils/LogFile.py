"""This module exposes the Log class as a parent of File."""

import pandas as pd
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import matplotlib.pyplot as plt
import numpy as np

from .GenericFile import File

DIGIT_REGEX = re.compile(r"(\d+(\.\d+)?)")


class Presets(tuple[str, ...], Enum):
    """A class to represent plotting presets."""

    MISC = (" ping", " ram_usage", " gpu_core_usage")
    GPU = (" gpu_temp", " gpu_core_usage", " gpu_power")
    TEMPS = (" system_temp", " gpu_temp", " cpu_temp")
    CPU = (" cpu_max_clock", " cpu_avg_clock")
    VOLTS = (" gpu_voltage", " cpu_voltage")


@dataclass
class LogMetaData:
    """A class to represent a log entry."""

    path: str = field(default_factory=str, repr=False)
    sep: str = field(default=",")
    encoding: str = field(default="iso-8859-1")
    _df: pd.DataFrame = field(default_factory=pd.DataFrame, repr=False)


class Log(LogMetaData, File):
    """A class to represent a log file."""

    presets = Presets

    def __init__(self, path: str, sep: str = ",", encoding: str = "iso-8859-1"):
        """Initialize the File and Log classes with the given parameters."""
        File.__init__(self, path, encoding=encoding)
        LogMetaData.__init__(self, path, sep, encoding)

    @property
    def df(self) -> pd.DataFrame:
        """Parse the log file into a DataFrame."""
        if self._df.empty:
            self._df = pd.read_csv(
                self.path,
                sep=self.sep,
                encoding=self.encoding,
                engine="python",
                index_col=0,
            )
        return self._df

    def __hash__(self):
        """Return a hash of the log file."""
        return hash((type(self), self.md5_checksum()))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, type(self)):
            return False
        return hash(self) == hash(other)

    def plot(self, columns: tuple[str, ...] = Presets.TEMPS.value, smooth_factor=1) -> None:
        missing_columns = [col for col in columns if col not in self.df.columns]

        # Create index from timestamp
        self.df.index = pd.to_datetime(self.df.index)
        self.df.index = self.df.index.strftime("%H:%M")

        # Plot the data even if some of the specified columns are missing from the file
        if missing_columns:
            print(
                f"\033[33m[WARNING]\033[0m Columns \033[1;4m{", ".join(missing_columns)}\033[0m do not exist in the file."
            )
            columns = [col for col in columns if col in self.df.columns] or self.df.columns  # type: ignore
        print(columns)
        # Smooth the line for easier reading of large datasets
        smooth_data = {}
        if smooth_factor == 1:
            smooth_factor = int(self.df.shape[0] / 100) or 1
        for column in columns:
            smooth_data[column] = np.convolve(
                self.df[column], np.ones(smooth_factor) / smooth_factor, mode="valid"
            )

        smooth_df = pd.DataFrame(smooth_data, index=self.df.index[: -(smooth_factor - 1)])

        fig, ax = plt.subplots(
            figsize=(16, 6),
            dpi=80,
            edgecolor="#5a93a2",
            linewidth=1,
            tight_layout=True,
            facecolor="#364146",
            subplot_kw={"facecolor": "#2E3539"},
        )

        # Y-axis settings
        plt.ylabel("Value", fontsize=14, color="#d3c6aa", fontweight="bold")

        # X-axis settings
        plt.xlabel("")
        ax.set_xlim(left=0, right=len(smooth_df))
        print(len(smooth_df.columns))
        if len(self.df.columns) == 1:
            smooth_df.plot(
                ax=ax,
                grid=True,
                kind="line",
                color="#a7c080",
            )
        else:
            smooth_df.plot(ax=ax, grid=True, kind="line")

        # plt properties
        plt.grid(True, linestyle="--", alpha=0.3, color="#d3c6a2")
        plt.title(self.basename, fontsize=16, color="#d3c6a2", fontweight="bold")
        plt.legend(loc="upper left")

        # plt.yticks(fontsize=12, color="#d3c6aa")
        plt.xticks(rotation=45, fontsize=12, color="#d3c6aa")
        plt.show()

    def compare(self, other):
        """Compare two log files."""
        # Find common columns
        common_columns = set(self.df.columns).intersection(other.df.columns.tolist())
        # Create a new DataFrame with common columns with a length of min(self, other)
        df = pd.DataFrame(index=range(min(len(self.df), len(other.df))))
        for column in common_columns:
            df[column] = self.df[column].iloc[: len(df)] - other.df[column].iloc[: len(df)]
        df.plot()
