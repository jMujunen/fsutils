import pandas as pd
from dataclasses import dataclass, field
from enum import Enum


@dataclass
class Hwinfo:
    """Preset columns for plotting."""

    SEP: str = field(default=",")
    ENCODING: str = field(default="iso-8859-1")
    GPU_COLS: tuple[str, ...] = field(default=("GPU Power [W]",))
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

    SEP: str = field(default=r",\s+")
    ENCODING = "utf-8"
    MISC_COLS: tuple[str, ...] = field(default=("GPU1 Voltage(Milli Volts)",))
    GPU_COLS: tuple[str, ...] = field(default=("GPU1 Frequency(MHz)", "GPU1 Memory Frequency(MHz)"))
    USAGE_COLS: tuple[str, ...] = field(default=("CPU Utilization(%)", "GPU1 Utilization(%)"))
    LATENCY_COLS: tuple[str, ...] = field(
        default=("Render Latency(MSec)", "Average PC Latency(MSec)")
    )
    FPS_COLS: tuple[str, ...] = field(default=("FPS",))
    INDEX_COL = 0


@dataclass
class Custom:
    """Preset columns for plotting."""

    SEP: str = field(default=r",\s+")
    ENCODING = "utf-8"
    MISC_COLS: tuple[str, ...] = field(default=("ping", "ram_usage", "gpu_core_usage"))
    GPU_COLS: tuple[str, ...] = field(default=("gpu_temp", "gpu_core_usage", "gpu_power"))
    TEMP_COLS: tuple[str, ...] = field(default=("system_temp", "gpu_temp", "cpu_temp"))
    CPU_COLS: tuple[str, ...] = field(default=("cpu_max_clock", "cpu_avg_clock"))
    VOLT_COLS: tuple[str, ...] = field(default=("gpu_voltage", "cpu_voltage"))
    INDEX_COL = 0


@dataclass
class Gpuz:
    SEP: str = field(default=r"\s+,\s+")
    ENCODING: str = field(default="iso-8859-1")
    TEMP_COLS: tuple[str, ...] = field(
        default=(
            "GPU Temperature [°C]",
            "Hot Spot [°C]",
            "Memory Temperature [°C]",
            "CPU Temperature [°C]",
        )
    )
    USAGE_COLS: tuple[str, ...] = field(
        default=("GPU Usage [%]", "Memory Controller Load [%]", "Power Consumption (%) [% TDP]")
    )
    VOLT_COLS: tuple[str, ...] = field(default=("GPU Voltage [V]",))
    CLOCK_COLS: tuple[str, ...] = field(default=("GPU Clock [MHz]", "Memory Clock [MHz]"))
    MISC_COLS: tuple[str, ...] = field(default=("Board Power Draw [W]",))
    INDEX_COL = 0


class Presets(Enum):
    GPUZ = Gpuz
    HWINFO = Hwinfo
    CUSTOM = Custom
    NVIDIA = Nvidia
