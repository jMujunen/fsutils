"""This module exposes the Log class as a parent of Base."""

import contextlib
import pandas as pd
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from fsutils.file import Base

DIGIT_REGEX = re.compile(r"(\d+(\.\d+)?)")

type PresetType = Hwinfo | Nvidia | Custom | Ping | Gpuz


@dataclass
class Hwinfo:
    """Preset columns for plotting."""

    SEP: str = ","
    ENCODING: str = "iso-8859-1"
    GPU_COLS: tuple[str, ...] = ("GPU Power [W]",)
    TEMP_COLS: tuple[str, ...] = (
        "System Temp [°C]",
        "CPU Package [°C]",
        "GPU Temperature [°C]",
        "GPU Memory Junction Temperature [°C]",
        "GPU Hot Spot Temperature [°C]",
    )

    FPS_COLS: tuple[str, ...] = (
        "Framerate (Presented) [FPS]",
        "Framerate (Displayed) [FPS]",
        "Framerate [FPS]",
        "Framerate 1% Low [FPS]",
        "Framerate 0.1% Low [FPS]",
    )

    LATENCY_COLS: tuple[str, ...] = (
        "Frame Time [ms]",
        "GPU Busy [ms]",
        "Frame Time [ms].1",
        "GPU Wait [ms]",
        "CPU Busy [ms]",
        "CPU Wait [ms]",
    )

    VOLT_COLS: tuple[str, ...] = ("Vcore [V]", "VIN3 [V]", "+12V [V]", "GPU Core Voltage [V]")

    INDEX_COL: int = 1


@dataclass
class Nvidia:
    """Presets."""

    SEP: str = r",\s+"
    ENCODING: str = "utf-8"
    MISC_COLS: tuple[str, ...] = ("GPU1 Voltage(Milli Volts)",)
    GPU_COLS: tuple[str, ...] = ("GPU1 Frequency(MHz)", "GPU1 Memory Frequency(MHz)")
    USAGE_COLS: tuple[str, ...] = ("CPU Utilization(%)", "GPU1 Utilization(%)")
    LATENCY_COLS: tuple[str, ...] = ("Render Latency(MSec)", "Average PC Latency(MSec)")
    FPS_COLS: tuple[str, ...] = ("FPS",)
    TEMP_COLS: tuple[str, ...] = ("",)
    INDEX_COL: int = 0


@dataclass
class Custom:
    """Preset columns for plotting."""

    SEP: str = r",\s+"
    ENCODING: str = "utf-8"
    MISC_COLS: tuple[str, ...] = ("ping", "ram_usage", "gpu_core_usage")
    GPU_COLS: tuple[str, ...] = ("gpu_temp", "gpu_core_usage", "gpu_power")
    TEMP_COLS: tuple[str, ...] = ("sys_temp", "gpu_core_temp", "cpu_max_temp")
    CPU_COLS: tuple[str, ...] = ("cpu_max_clock", "cpu_avg_clock")
    VOLT_COLS: tuple[str, ...] = ("gpu_voltage", "cpu_voltage")
    INDEX_COL: int = 0


@dataclass
class Ping:
    """Preset columns for plotting."""

    SEP: str = ","
    ENCODING: str = "utf-8"
    # MISC_COLS: tuple[str, ...] = lambda x: f'p
    GPU_COLS: None = None
    TEMP_COLS: None = None
    CPU_COLS: None = None
    VOLT_COLS: None = None
    INDEX_COL: int = 0
    _SANITIZER = re.compile(r"(\d{2}:\d{2}:\d{2},\d+\.\d+)")


@dataclass
class Gpuz:
    SEP: str = r"\s+,\s+"
    ENCODING: str = "iso-8859-1"
    TEMP_COLS: tuple[str, ...] = (
        "GPU Temperature [°C]",
        "Hot Spot [°C]",
        "Memory Temperature [°C]",
        "CPU Temperature [°C]",
    )

    USAGE_COLS: tuple[str, ...] = (
        "GPU Usage [%]",
        "Memory Controller Load [%]",
        "Power Consumption (%) [% TDP]",
    )

    VOLT_COLS: tuple[str, ...] = ("GPU Voltage [V]",)
    CLOCK_COLS: tuple[str, ...] = ("GPU Clock [MHz]", "Memory Clock [MHz]")
    MISC_COLS: tuple[str, ...] = ("Board Power Draw [W]",)
    INDEX_COL: int = 0


class Presets:
    GPUZ = Gpuz
    HWINFO = Hwinfo
    CUSTOM = Custom
    NVIDIA = Nvidia
    PING = Ping


@dataclass
class LogMetaData:
    """A class to represent a log entry."""

    path: str = field(default_factory=str, repr=False, init=True)
    encoding: str = field(default="iso-8859-1", repr=True, init=True, kw_only=True)
    df: pd.DataFrame = field(default_factory=pd.DataFrame, repr=False)
    preset: type = field(default=Presets.CUSTOM, repr=False, init=True, kw_only=True)

    def __post_init__(self):
        self.pathlibpath = Path(self.path)
        if not self.pathlibpath.exists():
            raise FileNotFoundError("The file does not exist.")
        if self.pathlibpath.suffix.lower() not in {".csv", ".txt", ".log"}:
            raise ValueError("The file is not a valid log file.")
        self.__dict__.update(self.preset().__dict__)

        with contextlib.suppress(Exception):
            self.df = pd.read_csv(
                self.path,
                sep=self.preset.SEP,
                encoding=self.preset.ENCODING,
                engine="python",
                index_col=self.preset.INDEX_COL,
            ).head(-5)
            for col in self.df.columns:
                with contextlib.suppress(ValueError):
                    self.df[col] = self.df[col].astype(float)

            self.df.drop(columns=["Date"], inplace=True)


class Log(Base, LogMetaData):
    """A class to represent a log file."""

    presets: type = Presets

    def __init__(
        self,
        path: str,
        encoding: str = "iso-8859-1",
        **kwargs: Any,
    ) -> None:
        """Initialize the File and Log classes with the given parameters."""
        self.encoding = encoding
        LogMetaData.__init__(self, path=path, **kwargs)
        super().__init__(path, encoding)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, type(self)):
            return False
        return hash(self) == hash(other)

    def plot(self, columns: tuple[str, ...] = Custom.TEMP_COLS, smooth_factor=1) -> None:
        missing_columns = [col for col in columns if col not in self.df.columns]
        columns_to_plot = columns

        if hasattr(self.preset, "_SANITIZER"):
            parsed_data: list[tuple] = [
                (x, float(y))
                for x, y in [
                    line.strip().split(",")
                    for line in self.read_text().splitlines()
                    if self.preset._SANITIZER.match(line)
                ]
            ]
            self.df = pd.DataFrame(parsed_data).set_index(0)
        # Create index from timestamp
        r"""if re.match(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}", str(self.df.index[0])):
        self.df.index = self.df[self.df.columns[self.INDEX_COL]]
        self.df.drop(self.df.columns[self.INDEX_COL])"""

        self.df.index = pd.to_datetime(self.df.index)
        self.df.index = self.df.index.strftime("%H:%M")

        missing_columns = set(columns) - set(columns_to_plot)
        # Plot the data even if some of the specified columns are missing from the file
        if missing_columns:
            print(
                f"\033[33m[WARNING]\033[0m Columns \033[1;4m{', '.join(missing_columns)}\033[0m do not exist in the file."
            )
            columns_to_plot = [col for col in columns if col in self.df.columns] or self.df.columns

        # Smooth the line for easier reading of large datasets
        smooth_data = {}
        smooth_df: pd.DataFrame = pd.DataFrame()

        if smooth_factor == 1:
            smooth_factor = int(self.df.shape[0] / 100) or 1
            for column in columns_to_plot:
                try:
                    smooth_data[column] = np.convolve(
                        self.df[column], np.ones(smooth_factor) / smooth_factor, mode="valid"
                    )
                    smooth_df = pd.DataFrame(
                        smooth_data, index=self.df.index[: -(smooth_factor - 1)]
                    )
                except ValueError as e:
                    print(f"\033[31m[ERROR]\033[0m Could not smooth data for column {column}: {e}")
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
        plt.title(self.name, fontsize=16, color="#d3c6a2", fontweight="bold")
        plt.legend(loc="upper left")

        # plt.yticks(fontsize=12, color="#d3c6aa")
        plt.xticks(rotation=45, fontsize=12, color="#d3c6aa")
        plt.show()

    def wrangle(self) -> None:
        """Sanitize the log file."""
        self.df = self.df.select_dtypes(include="number")

    def correlation(self) -> None:
        """Calculate the correlation between columns in the log file."""
        correlation_matrix = self.df.corr(method="pearson")
        plt.figure(
            figsize=(16, 10),
            dpi=80,
            tight_layout=True,
        )
        sns.heatmap(
            correlation_matrix,
            annot=True,
            fmt=".2f",
            cmap="coolwarm",
            center=0,
            cbar=True,
            xticklabels=True,
            yticklabels=True,
            linecolor="#364146",
            linewidths=0.5,
        )
        plt.title("Correlation Matrix Heatmap")
        plt.show()

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name}, shape={self.df.shape}, SEP=r'{self.SEP}', size_human={self.size_human})"  # type: ignore

    def __hash__(self):
        """Return a hash of the log file."""
        return super().__hash__()
        # return hash((type(self), self.md5_checksum()))

    def compare(self, other: "Log") -> pd.DataFrame:
        """Compare two log files."""
        rows = min(len(self.df), len(other))

        df = self.df.head(rows)
        df.index = range(len(df))

        other_df = other.df.head(rows)
        other_df.index = range(len(other_df))

        return df.compare(other_df)


if __name__ == "__main__":
    logfile = "/tmp/hwinfo.csv"

    log = Log(logfile, preset=Log.presets.CUSTOM)
    log.plot()
