"""This type stub file was generated by cyright."""

import os
from typing import Optional
from collections.abc import Generator, Iterator
from fsutils.img import Img
from fsutils.video import Video
from fsutils.file.GenericFile import File
from fsutils.utils.decorators import exectimer

"""Represents a directory. Contains methods to list objects inside this directory."""

class Dir(File):
    """A class representing information about a directory.

    Attributes
    ----------
        - `path (str)` : The path to the directory.

    Methods
    -------
        - `file_info (other)` :     # Check for `other` in self and return it as an object of `other`
        - `getinfo()` :             # Returns a list of extentions and their count
        - `__eq__ (other)` :        # Compare properties of two Dir objects
        - `__contains__ (other)` :  # Check if `other` is present in self
        - `__len__`:                # Return the number of objects in self
        - `__iter__`  :             # Iterator which yields the appropriate File instance


    Properties
    -----------
        - `files`       : Read only property returning a list of file names
        - `objects`     : Read-only property yielding a sequence of DirectoryObject or FileObject instances
        - `directories` : Read-only property yielding a list of absolute paths for subdirectories

    """
    def __init__(self, path: str | None = ..., mkdir: bool = False) -> None:
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

    def videos(self) -> Generator[Video, None, None]:
        """Return a generator of Video objects for all video files."""

    def images(self) -> Generator[Img, None, None]:
        """Return a generator of Img objects for all image files."""

    def non_media(self) -> list[File]:
        """Return a generator of all files that are not media."""

    def describe(self, print_result: bool = True) -> dict[str, int]:
        """Print a formatted table of each file extention and their count."""

    @property
    def db(self) -> dict[str, list[str]] | None: ...
    @property
    def size(self) -> int:
        """Return the total size of all files and directories in the current directory."""

    @property
    def size_human(self) -> str: ...
    def duplicates(self, num_keep: int = 2, updatedb: bool = False) -> list[list[str]]:
        """Return a list of duplicate files in the directory.

        Uses pre-calculated hash values to find duplicates.

        Paramaters:
        -----------
            - num_keep (int): The number of copies of each file to keep.
            - updatedb (bool): If True, re-calculate the hash values for all files
        """

    def load_database(self) -> dict[str, list[str]]:
        """Deserialize the pickled database."""

    def serialize(self, replace: bool = False, progress_bar: bool = True) -> dict[str, list[str]]:
        """Create an hash index of all files in self."""

    def compare(self, other: Dir) -> tuple[set[str], set[str]]:
        """Compare the current directory with another directory."""

    def ls(
        self, follow_symlinks: bool = True, recursive: bool = ...
    ) -> Generator[os.DirEntry, None, None]: ...
    def ls_dirs(self, follow_symlinks: bool = True) -> Generator[str, None, None]:
        """Return a list of paths for all directories in self."""

    def ls_files(self, follow_symlinks: bool = True) -> Generator[str, None, None]:
        """Return a list of paths for all files in self."""
    def fileobjects(self) -> list[File]:
        """Return a list of File instances for each item in self."""
    def traverse(
        self, root=..., follow_symlinks: bool = True
    ) -> Generator[os.DirEntry, None, None]:
        """Recursively traverse a directory tree starting from the given path.

        Yields
        ------
            Generator[os.DirEntry]
        """

    def __getitem__(self, key: str) -> Generator[File, None, None]:
        """Get a file by name."""

    def __format__(self, format_spec: str, /) -> str: ...
    def __contains__(self, other: File) -> bool:
        """Is `File` in self?"""

    def __hash__(self) -> int: ...
    def __len__(self) -> int:
        """Return the number of items in the object."""

    def __iter__(self) -> Iterator[File]:
        """Yield a sequence of File instances for each item in self."""

    def __eq__(self, other: Dir, /) -> bool:
        """Compare the contents of two Dir objects."""

    @exectimer
    def __repr__(self) -> str: ...

def obj(file_path: str) -> File:
    """Return a File instance for the given file path."""