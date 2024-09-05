"""Base class and building block for all other classes defined in this library."""

import hashlib
import os
import re
import shutil
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any

import chardet
from size import Size

from .mimecfg import FILE_TYPES

GIT_OBJECT_REGEX = re.compile(r"([a-f0-9]{37,41})")


@dataclass
class FileMetadata:
    """Hold file metadata."""

    path: str
    encoding: str = field(default="utf-8")

    def __post_init__(self):
        self.path = os.path.abspath(self.path)
        if not os.path.exists(self.path):
            raise FileNotFoundError(f"{self.path} does not exist")
        self.filename = os.path.basename(self.path)
        self.extension = os.path.splitext(self.path)[-1]
        self.size = os.path.getsize(self.path)
        self.size_human = Size(self.size)
        self.st = os.stat(self.path)
        self.dirname = os.path.dirname(self.path)


class File(FileMetadata):
    """This is the base class for all of the following objects.

    It represents a generic file and defines the common methods that are used by all of them.

    It can be used standlone (Eg. text based files) or as a parent class for other classes.

    Attributes:
    ----------
        - `encoding (str)` : The encoding to use when reading/writing the file. Defaults to utf-8.
        - `path (str)` : The absolute path to the file.
        - `content (Any)` : Contains the content of the file. Only holds a value if read() is called.

    Properties:
    ----------
        - `size` : The size of the file in bytes.
        - `file_name` : The name of the file without its extension.
        - `extension` : The extension of the file (Eg. file.out.txt -> file.out)
        - `basename` : The basename of the file (Eg. file.out.txt)
        - `is_file` : Check if the objects path is a file
        - `is_executable` : Check if the object has an executable flag
        - `is_image` : Check if item is an image
        - `is_video` : Check if item is a video
        - `is_gitobject` : Check if item is a git object
        - `is_link` : Check if item is a symbolic link
        - `content` : The content of the file. Only holds a value if read() is called.

    Methods:
    ----------
        - `read()` : Return the contents of the file
        - `head(self, n=5)` : Return the first n lines of the file
        - `tail(self, n=5)` : Return the last n lines of the file
        - `detect_encoding()` : Return the encoding of the file based on its content
        - `__eq__()` : Compare properties of FileObjects
        - `__str__()` : Return a string representation of the object

    """

    def __init__(self, path: str, encoding: str = "utf-8") -> None:
        """Init for the object.

        Paramaters:
        ----------
            - `path (str)` : The path to the file
            - `encoding (str)` : Encoding type of the file (default is utf-8)
        """
        super().__init__(path=path, encoding=encoding)

    def head(self, n: int = 5) -> list[str]:
        """Return the first n lines of the file."""
        if self.content is not None and len(self.content) > n:
            return self.content[:n]
        return self.content

    def tail(self, n: int = 5) -> list[str]:
        """Return the last n lines of the file."""
        if self.content is not None:
            return self.content[-n:]
        return self.content

    @property
    def exists(self) -> bool:
        return os.path.exists(self.path)

    @property
    def content(self) -> list[Any]:
        """Helper for self.read()."""
        if not self._content:
            self._content = self.read()
        return self._content

    def read(self, **kwargs) -> list[Any]:
        """Read the content of a file.

        While this method is cabable of reading certain binary data, it would be good
        practice to override this method in subclasses that deal with binary files.

        Kwargs:
        ------------
            a=0, b=~ (optional): Return lines[a:b]
            refresh (optional): If True, the method will re-read the file from disk. Defaults to False.
        Returns:
        ----------
            str: The content of the file
        """
        if not self._content or kwargs.get("refresh", False):
            try:
                with open(self.path, "rb") as f:
                    lines = f.read().decode(self.encoding).split("\n")
                    content = list(lines[kwargs.get("a", 0) : kwargs.get("b", len(lines))])
            except Exception:
                try:
                    with open(self.path, encoding=self.encoding) as f:
                        content = f.readlines()
                except Exception:
                    try:
                        with open(self.path, "rb") as f:
                            content = f.readlines()
                    except Exception as e:
                        raise TypeError(f"Reading {type(self)} is unsupported") from e
            self._content = content or self._content
        return (
            self._content[kwargs.get("a", 0) : kwargs.get("b", len(self._content))]
            if kwargs
            else self._content
        )

    def _read_chunk(self, size=8192) -> bytes:
        """Read a chunk of the file and return it as bytes."""
        with open(self.path, "rb") as f:
            return f.read(size)

    @property
    def md5_checksum(self, size=8192) -> str:
        """Return the MD5 checksum of a portion of the image file."""
        data = self._read_chunk(size)
        return hashlib.md5(data).hexdigest()

    @property
    def st(self) -> os.stat_result:
        """Run `stat` on the file."""
        return os.stat(self.path)

    @property
    def mode(self) -> int:
        """Get UNIX EXT4 file permissions."""
        return int(oct(self.st.st_mode)[-3:])

    @mode.setter
    def mode(self, value: int) -> None:
        """Set UNIX EXT4 file permissions."""
        value = int(f"0o{value}")
        os.chmod(self.path, value)

    def detect_encoding(self) -> str | None:
        """Detect encoding of the file."""
        with open(self.path, "rb") as f:
            return chardet.detect(f.read())["encoding"]

    # def __hash__(self) -> int:
    #     try:
    #         return hash(("\n".join(self.content), self.size))
    #     except TypeError:
    #         return hash((self.md5_checksum, self.size))

    def __iter__(self) -> Iterator[str]:
        """Iterate over the lines of a file."""
        if self.content is not None:
            try:
                for line in self.content:
                    yield (str(line).strip())
            except TypeError as e:
                raise TypeError(f"Object of type {type(self)} is not iterable: {e}") from e

    def __len__(self) -> int:
        """Get the number of lines in a file."""
        try:
            return len(list(iter(self)))
        except Exception as e:
            raise TypeError(f"Object of type {type(self)} does not support len(): {e}") from e

    def __contains__(self, item: Any) -> bool:
        """Check if a line exists in the file.

        Parameters:
        ----------
            item (str): The line to check for

        """
        return any(item in line for line in self) or any(
            item in word for word in item.split(" ") for line in self
        )

    def __eq__(self, other: "File", /) -> bool:
        """Compare two FileObjects.

        Paramaters:
        -----------
            other (Object): The Object to compare (FileObject, VideoObject, etc.)

        """
        return all((other.exists, self.exists, hash(self) == hash(other)))

    def __str__(self) -> str:
        try:
            return "\n".join(self.content)
        except TypeError:
            return self.__repr__()
