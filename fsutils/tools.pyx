# language_level=3
"""Helper functions."""

from datetime import timedelta
from enum import Enum

import numpy as np
from enum import Enum

SECONDS_PER_HOUR = 60 * 60


class SizeUnit(Enum):
    B = 1
    KB = 1024
    MB = 1024**2
    GB = 1024**3
    TB = 1024**4


class SizeUnit(Enum):
    B = 1
    KB = 1024
    MB = 1024**2
    GB = 1024**3
    TB = 1024**4


def format_timedelta(td: timedelta) -> str:
    """Format timedelta objects omitting microseconds and retaining milliseconds."""
    result = str(td)
    try:
        result, ms = result.split(".")
    except ValueError:
        return (result + ".00").replace(":", "-")
    ms = int(ms)
    ms = round(ms / 1e4)
    return result.replace(":", "-") + f".{ms}"


def frametimes(num_frames: int, clip_fps: int, saving_fps: int) -> list[int]:
    """Return the list of durations where to save the frames."""
    print("num frames:", num_frames)
    print("clip fps:", clip_fps)
    print("saving fps:", saving_fps)
    s = []
    duration = num_frames / clip_fps
    print("duration:", duration)
    # use np.arange() to make floating-point steps
    for i in np.arange(0, duration, 1 / saving_fps):
        s.append(i)
    return s


def format_bytes(raw_bytes: int):
    """Convert bytes to the appropriate unit (B, KB, MB, GB, or TB)."""
    size = raw_bytes
    for unit in SizeUnit:
        if size < SizeUnit.KB.value:
            return f"{size:.2f} {unit.name}"
        size /= 1024

    return f"{size / 1024:.2f} {SizeUnit.TB.name}"  # Last unit is TB
