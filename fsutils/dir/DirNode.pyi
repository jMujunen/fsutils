import os
from collections.abc import Generator, Iterator
from enum import Enum

import cython

from fsutils.file.GenericFile import Base
from fsutils.img import Img
from fsutils.video import Video

"""Represents a directory. Contains methods to list objects inside this directory."""

class Dir(Base):
    """A class representing information about a directory.

    Attributes
    ----------
        - `path (str)` : The path to the directory.

    Methods
    -------
        - `describe()` :            # Returns a list of extentions and their count
        - `compare(other)` :        # Compare properties of two Dir objects
        - `duplicates(num_keep=2)`   # Returns a list of duplicate files in this directory
        - `filter(ext)` :           # Returns a list of files that match the given extension
        - `glob(pattern)` :         # Returns a list of files that match the given pattern
        - `is_empty()` :            # Returns True if the directory is empty, False otherwise
        - `load_database()` :       # Load indexed database
        - `ls()` :                  # List the contents of the toplevel directory
        - `ls_dirs()` :             # List the contents of the toplevel directory as directories
        - `traverse()` :             # Traverse the directory tree and yield all files
        - `serialize()` :           # Serialize the directory index
        - `non_media()` :           # Returns a list of non-media files in this directory
        - `videos()` :              # Returns a list of video objects in this directory
        - `images()` :              # Returns a list of image objects in this directory
        - `fileobjects()` :         # Returns a list of files objects in this directory

    Properties
    -----------
        - `files`       : Read only property returning a list of file names
        - `dirs` : Read-only property yielding a list of absolute paths for subdirectories
        - `content` : List the the contents of the toplevel directory
        - `size`  : Read-only property returning the size of the directory in bytes.
        - `size_human`  : Read-only property returning the size of the directory in human readable format.

    """
    def __cinit__(self, path: str = ...) -> None:
        """Fast __new__."""

    def __init__(self, path: str = ...) -> None:
        """Initialize a new instance of the Dir class.

        Parameters
        ----------
            path (str) : The path to the directory.

        """

    @property
    def dirs(self) -> list[str]:
        """Return a list of all directories in the directory."""

    @property
    def files(self) -> list[str]:
        """Return a list of all files in the directory."""

    @property
    def content(self) -> list[str]:
        """List the the contents of the toplevel directory."""

    def is_empty(self) -> bool:
        """Check if the directory is empty."""

    def videos(self, *, init: bool = ...) -> list[Video]: ...
    def images(self, *, init: bool = ...) -> list[Img]: ...
    def non_media(self) -> list[Base]:
        """Return a generator of all files that are not media."""

    def fileobjects(self, *, init: bool = ...) -> list[Base]:
        """Return a list of all file objects."""

    @cython.wraparound(False)
    @cython.boundscheck(False)
    def describe(self, print_result: bool = ...) -> dict[str, int]:
        """Print a formatted table of each file extention and their count."""

    # @property
    # def db(self) -> dict[str, set[str]]: ...
    # @db.setter
    # def db(self, value: dict[str, set[str]]):  # -> None:
    #     ...
    @property
    def size(self) -> int:
        """Size of all files and directories in the current directory."""

    @property
    def size_human(self) -> str:
        """Size of directory in human-readable format."""

    @cython.wraparound(False)
    @cython.boundscheck(False)
    def duplicates(self, num_keep: int = ..., updatedb: bool = ...) -> list[list[str]]:
        """Return a list of duplicate files in the directory.

        Uses pre-calculated hash values to find duplicates.

        Paramaters:
        -----------
            - num_keep (int): The number of copies of each file to keep.
            - updatedb (bint): If True, re-calculate the hash values for all files
        """

    @property
    def db(self) -> dict[str, set[str]]: ...
    @db.setter
    def db(self, value: dict[str, set[str]]):  # -> None:
        ...
    def _load_database(self) -> dict[str, set[str]]:
        """Deserialize the pickled database."""

    @cython.wraparound(False)
    @cython.boundscheck(False)
    def serialize(self, *, replace: bool = ...) -> dict[str, set[str]]:
        """Create an hash index of all files in self.

        Paramaters
        ----------
            - replace (bint): If True, re-calculate the hash values for all files

        Returns
        -------
            - dict[str, set[str]]: A dictionary where the keys are hash values
                and the values are lists of file paths.

        """

    def compare(self, other: Dir) -> tuple[set[str], set[str]]:
        """Compare the current directory with another directory."""

    def ls(
        self, follow_symlinks: bool = ..., recursive: bool = ...
    ) -> Generator[os.DirEntry]: ...
    def ls_dirs(self, follow_symlinks: bool = ...) -> Generator[str]:
        """Return a list of paths for all directories in self."""

    def ls_files(self, follow_symlinks: bool = ...) -> Generator[str]:
        """Return a list of paths for all files in self."""

    def traverse(self, root=..., follow_symlinks: bool = ...) -> Generator[os.DirEntry]:
        """Recursively traverse a directory tree starting from the given path.

        Yields
        ------
            Generator[os.DirEntry]
        """

    def filter(self, ext: str) -> list[Base]:
        """Filter files by extension."""

    def glob(self, pattern: str) -> list[Base]:
        """Filter files by glob pattern."""

    def __getitem__(self, key: str | Base, /) -> list[Base]:
        """Get a file by name or instance."""

    def __format__(self, format_spec: str, /) -> str: ...
    def __hash__(self) -> int: ...
    def __len__(self) -> int:
        """Return the number of items in the object."""

    def __contains__(self, item: Base) -> bool: ...
    def __iter__(self) -> Iterator[Base]:
        """Yield a sequence of Base instances for each item in self."""

    def __eq__(self, other: Dir, /) -> bool:
        """Compare the contents of two Dir objects."""

    def __repr__(self) -> str: ...

class FileType(Enum):
    img = ...
    video = ...
    def __init__(self, extensions: tuple[str], cls) -> None: ...

EXTENSION_MAP: dict[str, Base] = ...

class File:
    def __new__(cls, filepath: str, *, init: bool = ...) -> Base: ...
    @staticmethod
    def from_hash(hash: str, db: dict[str, set[str]]) -> list[Base]: ...
