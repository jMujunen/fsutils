"""This module exposes the Log class as a parent of File."""

import pandas as pd
import re
from dataclasses import dataclass, field
from typing import Any, ClassVar

import matplotlib.pyplot as plt
import numpy as np

from GenericFile import File

from .Presets import Presets

DIGIT_REGEX = re.compile(r"(\d+(\.\d+)?)")


class Log(File):
    """A class to represent a log file."""

    presets: type = Presets
    encoding: ClassVar[str] = "iso-8859-1"
    _df: pd.DataFrame = pd.DataFrame()

    def __init__(
        self,
        path: str,
        preset: Presets = Presets.CUSTOM,
        **kwargs: Any,
    ) -> None:
        """Initialize the File and Log classes with the given parameters."""
        self.__dict__.update(kwargs)
        super().__init__(path, self.encoding)
        self.preset = preset.value

    @property
    def df(self) -> pd.DataFrame:
        """Parse the log file into a DataFrame.

        Parameters
            presets (tuple[str,...])
        """
        if self._df.is_empty:
            self._df = pd.read_csv(
                self.path,
                sep=rf"{self.SEP}",  # type: ignore
                encoding=self.encoding,
                engine="python",
                index_col=self.preset.value.INDEX_COL,
            )
            self.__dict__.update(self._df)
        return self._df

    def plot(
        self, columns: tuple[str, ...] = Presets.CUSTOM.value.MISC_COLS, smooth_factor=1
    ) -> None:
        """Plot the specified columns of the log file.

        Parameters
            - columns (tuple[str, ...]): The names of the columns to plot. Defaults to Custom.TEMP_COLS.
            - smooth_factor (int): Smooth the data for easier reading of large datasets. Defaults to 1.

        Returns
            None
        """
        missing_columns = [col for col in columns if col not in self.df.columns]

        # Create index from timestamp
        # if re.match(r"\d{4}-\d{2}-\d{2}  \d{2}:\d{2}", str(self.df.index[0])):
        self.df.index = pd.to_datetime(self.df.index)
        self.df.index = self.df.index.strftime("%H:%M")
        # Plot the data even if some of the specified columns are missing from the file
        if missing_columns:
            print(
                f"\033[33m[WARNING]\033[0m Columns \033[1;4m{', '.join(missing_columns)}\033[0m do not exist in the file."
            )
            columns = [col for col in columns if col in self.df.columns] or self.df.columns  # type: ignore
        print(columns)
        # Smooth the line for easier reading of large datasets
        smooth_data = {}
        if smooth_factor == 1:
            smooth_factor = int(self.df.shape[0] / 100) or 1
        try:
            for column in columns:
                smooth_data[column] = np.convolve(
                    self.df[column], np.ones(smooth_factor) / smooth_factor, mode="valid"
                )
            smooth_df = pd.DataFrame(smooth_data, index=self.df.index[: -(smooth_factor - 1)])

        except:
            print(f"\033[31m[ERROR]\033[0m Could not smooth data for column {column}")
            smooth_df = self.df

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
        # Find common columns"(.*)",
        # common_columns = set(self.df.columns).intersection(other.df.columns.tolist())
        df = self.df.head(min(len(self.df), len(other.df)))
        other_df = other.df.head(min(len(self.df), len(other.df)))
        print(len(df))
        print(len(other_df))
        print(df.columns)
        print(other_df.columns)
        print(df)
        print(other_df)
        return df.compare(other_df)

    def sanatize(self):
        """Sanitize the log file."""
        header = self.head
