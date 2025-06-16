"""This provides a Dir for representing directories in a filesystem
and Base for dynamically instantiating objects based on file extensions."""

from .DirNode import Dir, File

__all__ = ["Dir", "File"]
