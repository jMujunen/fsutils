"""This module exposes the Log class as a parent of File."""

import contextlib
import pandas as pd
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
from GenericFile import File

DIGIT_REGEX = re.compile(r"(\d+(\.\d+)?)")


@dataclass
class Hwinfo:
    """Preset columns for plotting."""

    SEP: str = ","
    ENCODING: str = "iso-8859-1"
    GPU_COLS: tuple[str, ...] = ("GPU Power [W]",)
    TEMP_COLS: tuple[str, ...] = field(
        default=(
            "System Temp [°C]",
            "CPU Package [°C]",
            "GPU Temperature [°C]",
            "GPU Memory Junction Temperature [°C]",
            "GPU Hot Spot Temperature [°C]",
        )
    )
    FPS_COLS: tuple[str, ...] = field(
        default=(
            "Framerate (Presented) [FPS]",
            "Framerate (Displayed) [FPS]",
            "Framerate [FPS]",
            "Framerate 1% Low [FPS]",
            "Framerate 0.1% Low [FPS]",
        )
    )
    LATENCY_COLS: tuple[str, ...] = field(
        default=(
            "Frame Time [ms]",
            "GPU Busy [ms]",
            "Frame Time [ms].1",
            "GPU Wait [ms]",
            "CPU Busy [ms]",
            "CPU Wait [ms]",
        )
    )
    VOLT_COLS: tuple[str, ...] = field(
        default=("Vcore [V]", "VIN3 [V]", "+12V [V]", "GPU Core Voltage [V]")
    )

    INDEX_COL = 1


@dataclass
class Nvidia:
    """Presets."""

    SEP: str = r",\s+"
    ENCODING = "utf-8"
    MISC_COLS: tuple[str, ...] = ("GPU1 Voltage(Milli Volts)",)
    GPU_COLS: tuple[str, ...] = ("GPU1 Frequency(MHz)", "GPU1 Memory Frequency(MHz)")
    USAGE_COLS: tuple[str, ...] = ("CPU Utilization(%)", "GPU1 Utilization(%)")
    LATENCY_COLS: tuple[str, ...] = field(
        default=("Render Latency(MSec)", "Average PC Latency(MSec)")
    )
    FPS_COLS: tuple[str, ...] = ("FPS",)
    INDEX_COL = 0


@dataclass
class Custom:
    """Preset columns for plotting."""

    SEP: str = r",\s+"
    ENCODING = "utf-8"
    MISC_COLS: tuple[str, ...] = ("ping", "ram_usage", "gpu_core_usage")
    GPU_COLS: tuple[str, ...] = ("gpu_temp", "gpu_core_usage", "gpu_power")
    TEMP_COLS: tuple[str, ...] = ("system_temp", "gpu_temp", "cpu_temp")
    CPU_COLS: tuple[str, ...] = ("cpu_max_clock", "cpu_avg_clock")
    VOLT_COLS: tuple[str, ...] = ("gpu_voltage", "cpu_voltage")
    INDEX_COL = 0


@dataclass
class Ping:
    """Preset columns for plotting."""

    SEP: str = ","
    ENCODING = "utf-8"
    # MISC_COLS: tuple[str, ...] = lambda x: f'p
    GPU_COLS: None = None
    TEMP_COLS: None = None
    CPU_COLS: None = None
    VOLT_COLS: None = None
    INDEX_COL = 0
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

    USAGE_COLS: tuple[str, ...] = field(
        default=("GPU Usage [%]", "Memory Controller Load [%]", "Power Consumption (%) [% TDP]")
    )
    VOLT_COLS: tuple[str, ...] = ("GPU Voltage [V]",)
    CLOCK_COLS: tuple[str, ...] = ("GPU Clock [MHz]", "Memory Clock [MHz]")
    MISC_COLS: tuple[str, ...] = ("Board Power Draw [W]",)
    INDEX_COL = 0


class Presets(Enum):
    GPUZ = Gpuz
    HWINFO = Hwinfo
    CUSTOM = Custom
    NVIDIA = Nvidia
    PING = Ping


@dataclass
class LogMetaData:
    """A class to represent a log entry."""

    path: Path = field(default_factory=Path, repr=False, init=True)
    encoding: str = field(default="iso-8859-1", repr=True, init=True, kw_only=True)
    df: pd.DataFrame = field(default_factory=pd.DataFrame, repr=False)
    preset: type = field(default=Presets.CUSTOM.value, repr=False, init=True, kw_only=True)

    def __post_init__(self):
        if not self.path.exists():
            raise FileNotFoundError("The file does not exist.")
        if self.path.suffix not in [".csv", ".txt", ".log"]:
            return
        self.__dict__.update(self.preset().__dict__)

        with contextlib.suppress(Exception):
            self.df = pd.read_csv(
                self.path,
                sep=self.preset.SEP,
                encoding=self.encoding,
                engine="python",
                index_col=self.preset.INDEX_COL,
            )


class Log(File, LogMetaData):
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
        super().__init__(path, encoding)
        LogMetaData.__init__(self, path=Path(path), **kwargs)
        del self._content

    def __hash__(self):
        """Return a hash of the log file."""
        return hash((type(self), self.md5_checksum()))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, type(self)):
            return False
        return hash(self) == hash(other)

    def plot(self, columns: tuple[str, ...] = Custom.TEMP_COLS, smooth_factor=1) -> None:
        missing_columns = [col for col in columns if col not in self.df.columns]
        if hasattr(self.preset, "_SANITIZER"):
            parsed_data = [
                (x, float(y))
                for x, y in [
                    line.strip().split(",")
                    for line in self.read_text().splitlines()
                    if self.preset._SANITIZER.match(line)
                ]
            ]
            self.df = pd.DataFrame(parsed_data).set_index(0)
        # Create index from timestamp
        # if re.match(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}", str(self.df.index[0])):
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
        plt.title(self.name, fontsize=16, color="#d3c6a2", fontweight="bold")
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

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name}, shape={self.df.shape}, SEP=r'{self.SEP}', COLUMNS={[item for item in (vars(self.preset())) if item.endswith('COLS')]}"
