import os
from collections.abc import Iterator
from datetime import datetime
from typing import Any, NamedTuple

GIT_OBJECT_REGEX = ...
type times = tuple[datetime, datetime, datetime]

class Base:
    """This is the base class for all of the following objects.

    It represents a generic file and defines the common methods that are used by all of them.

    It can be used standlone (Eg. text based files) or as a parent class for other classes.

    Attributes
    ----------
        - `encoding (str)` : The encoding to use when reading/writing the file. Defaults to utf-8.
        - `path (str)` : The absolute path to the file.

    Properties:
    ----------
        - `path` : The absolute path to the file.
        - `encoding` : The encoding of the file.


        - `size` : The size of the file in bytes.
        - `size_human` : The size of the file in a human readable format.

    Methods
    ----------
        - `read_text()` : Return the contents of the file as a string
        - `read_json()` : Return the contents of the file as a json object

        - `is_image()` : Check if item is an image
        - `is_video()` : Check if item is a video
        - `is_gitobject()` : Check if item is a git object
        - `is_dir()` : Check if the file is a directory
        - `exists()` : Check if the file exists

        - `detect_encoding()` : Return the encoding of the file based on its content

        - `times()` : Return a tuple with (atime, mtime, ctime) of the file.
        - `mtime()` : Return the last modified time of the file
        - `ctime()` : Return the creation time of the file
        - `atime()` : Return the last access time of the file

        - `head(self, n=5)` : Return the first n lines of the file
        - `tail(self, n=5)` : Return the last n lines of the file
        - `__eq__()` : Compare properties of FileObjects
        - `__str__()` : Return a string representation of the object

    """

    path: str
    encoding: str

    def __init__(self, path: str, encoding: str = ..., *args, **kwargs) -> None:
        """Construct the Base object.

        Paramaters:
        ----------
            - `path (str)` : The path to the file
            - `encoding (str)` : Encoding type of the file (default is utf-8)
        """

    def head(self, n: int = ...) -> list[str]:
        """Return the first n lines of the file."""

    def tail(self, n: int = ...) -> list[str]:
        """Return the last n lines of the file."""

    def stat(self) -> os.stat_result:
        """Call os.stat() on the file path."""

    @property
    def name(self) -> str:
        """Return the file name with extension."""

    @property
    def parent(self) -> str:
        """Return the parent directory path of the file."""

    @property
    def size_human(self) -> str:
        """Return the size of the file in human readable format."""

    @property
    def size(self) -> int:
        """Return the size of the file in bytes."""

    @property
    def prefix(self) -> str:
        """Return the file name without extension."""

    @property
    def suffix(self) -> str:
        """Return the file extension."""

    @suffix.setter
    def suffix(self, value: str) -> None:
        """Set the file extension."""

    def is_binary(self) -> bool:
        """Check for null bytes in the file contents, telling us its binary data."""

    def is_gitobject(self) -> bool:
        """Check if the file is a git object."""

    def is_image(self) -> bool:
        """Check if the file is an image."""

    def is_video(self) -> bool:
        """Check if the file is a video."""

    @property
    def mtime(self) -> datetime:
        """Return the last modification time of the file."""

    @property
    def ctime(self) -> datetime:
        """Return the last metadata change of the file."""

    @property
    def atime(self) -> datetime:
        """Return the last access time of the file."""

    @property
    def parts(self) -> tuple[str, ...]: ...
    def times(self) -> times:
        """Return access, modification, and creation times of a file."""

    def exists(self) -> bool:
        """Check if the file exists."""

    def __iter__(self) -> Iterator[str | bytes]:
        """Iterate over the lines of a file."""

    def __len__(self) -> int:
        """Get the number of lines in a file."""

    def __contains__(self, item: Any) -> bool:
        """Check if a line exists in the file.

        Parameters
        ----------
            item (str): The line to check for

        """

    def __eq__(self, other: Base, /) -> bool:
        """Compare two FileObjects.

        Paramaters
        ----------
            other (Object): The Object to compare (FileObject, VideoObject, etc.)

        """
    def _read_chunk(self, chunk_size: int = 16384) -> bytes:
        """Read a chunk of the file.

        Args:
        -----
            chunk_size (int): The size of the chunk to read. Defaults to 16384 bytes.
        Returns:
        --------
            bytes: The chunk of data read from the file.
        """
    def __bool__(self) -> bool:
        """Check if the file exists."""

    def __repr__(self) -> str: ...
    def read_text(self) -> str:
        """Read the contents of the file as a string."""

    def sha256(self) -> str:
        """Compute and return the SHA-256 hash of the file."""

    def read_json(self) -> object: ...
    def __hash__(self) -> int:
        """Return the hash of the file."""

    def __str__(self) -> str:
        """Return a string representation of the file."""
