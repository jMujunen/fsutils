"""This module provides classes for working with video files and their metadata."""

from .FFProbe import FFProbe, Stream
from .VideoFile import Video

__all__ = ["FFProbe", "Stream", "Video"]
