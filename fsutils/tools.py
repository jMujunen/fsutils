"""Helper functions."""

from datetime import timedelta

import numpy as np

SECONDS_PER_HOUR = 60 * 60


def format_timedelta(td: timedelta) -> str:
    """Format timedelta objects omitting microseconds and retaining milliseconds."""
    result = str(td)
    try:
        result, ms = result.split(".")
    except ValueError:
        return (result + ".00").replace(":", "-")
    ms = int(ms)
    ms = round(ms / 1e4)
    return f"{result}.{ms:02}"


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
