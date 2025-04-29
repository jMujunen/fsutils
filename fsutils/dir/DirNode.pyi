from fsutils.file.GenericFile import Base
from fsutils.img import Img
from fsutils.video import Video
import os
from collections.abc import Generator, Iterator

class Dir(Base):
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
        - `dirs` : Read-only property yielding a list of absolute paths for subdirectories

    """

    path: str

    def __init__(self, path: str | None = ...) -> None:
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

    def videos(self) -> list[Video]: ...
    def images(self) -> list[Img]: ...
    def non_media(self) -> list[Base]:
        """Return a generator of all files that are not media."""

    def fileobjects(self) -> list[Base]:
        """Return a list of all file objects."""

    def describe(self, print_result: bool = ...) -> dict[str, int]:
        """Print a formatted table of each file extention and their count."""

    @property
    def db(self) -> dict[str, set[str]]: ...
    @db.setter
    def db(self, value: dict[str, set[str]]):  # -> None:
        ...
    @property
    def size(self) -> int:
        """Return the total size of all files and directories in the current directory."""

    @property
    def size_human(self) -> str: ...
    def duplicates(self, num_keep: int = ..., updatedb: bool = ...) -> list[list[str]]:
        """Return a list of duplicate files in the directory.

        Uses pre-calculated hash values to find duplicates.

        Paramaters:
        -----------
            - num_keep (int): The number of copies of each file to keep.
            - updatedb (bint): If True, re-calculate the hash values for all files
        """

    def _load_database(self) -> dict[str, set[str]]:
        """Deserialize the pickled database."""

    def serialize(self, replace: bool = ...) -> dict[str, set[str]]:
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

    def ls(self, follow_symlinks: bool = ..., recursive: bool = ...) -> Generator[os.DirEntry]: ...
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
        """Filter files by a glob pattern."""

    def __getitem__(self, key: str, /) -> list[Base]:
        """Get a file by name."""

    def __format__(self, format_spec: str, /) -> str: ...
    def __hash__(self) -> int: ...
    def __len__(self) -> int:
        """Return the number of items in the object."""

    def __contains__(self, item: Base) -> bool: ...
    def __iter__(self) -> Iterator[Base]:
        """Yield a sequence of File instances for each item in self."""

    def __eq__(self, other: Dir, /) -> bool:
        """Compare the contents of two Dir objects."""

    def __repr__(self) -> str: ...

def obj(file_path: str) -> Base:
    """Return a File instance for the given file path."""
