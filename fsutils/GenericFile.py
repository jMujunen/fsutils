"""Base class and building block for all other classes defined in this library."""

import hashlib
import os
import pickle
import re
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import chardet
from size import Size

from mimecfg import FILE_TYPES

GIT_OBJECT_REGEX = re.compile(r"([a-f0-9]{37,41})")


class File(Path):
    """This is the base class for all of the following objects.

    It represents a generic file and defines the common methods that are used by all of them.

    It can be used standlone (Eg. text based files) or as a parent class for other classes.

    Attributes
    ----------
        - `encoding (str)` : The encoding to use when reading/writing the file. Defaults to utf-8.
        - `path (str)` : The absolute path to the file.

    Properties:
    ----------
        - `size` : The size of the file in bytes.
        - `is_executable` : Check if the object has an executable flag
        - `is_image` : Check if item is an image
        - `is_video` : Check if item is a video
        - `is_gitobject` : Check if item is a git object
        - `content` : The content of the file. Only holds a value if read() is called.

    Methods
    ----------
        - `read()` : Return the contents of the file
        - `head(self, n=5)` : Return the first n lines of the file
        - `tail(self, n=5)` : Return the last n lines of the file
        - `detect_encoding()` : Return the encoding of the file based on its content
        - `__eq__()` : Compare properties of FileObjects
        - `__str__()` : Return a string representation of the object

    """

    def __new__(cls, *args, **kwargs):
        return super().__new__(cls, *args, **kwargs)

    def __init__(self, path: str | Path, encoding="utf-8", *args, **kwargs) -> None:
        """Construct the File object.

        Paramaters:
        ----------
            - `path (str)` : The path to the file
            - `encoding (str)` : Encoding type of the file (default is utf-8)
        """
        self.path = os.path.abspath(os.path.expanduser(path))
        self.encoding = encoding
        if not self.exists:
            raise FileNotFoundError(f"File '{self.path}' does not exist")
        self._content = []
        super().__init__(self.path, *args, **kwargs)

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
    def parent(self):
        """Return the parent directory path of the file."""
        return os.path.dirname(self.path)

    @property
    def size_human(self) -> str:
        """Return the size of the file in human readable format."""
        return str(Size(self.size))

    @property
    def size(self) -> int:
        """Return the size of the file in bytes."""
        return int(self.stat().st_size)

    @property
    def prefix(self) -> str:
        """Return the file name without extension."""
        return self.stem

    @property
    def is_binary(self) -> bool:
        """Check for null bytes in the file contents, telling us its binary data."""
        try:
            chunk = self._read_chunk(1024)
            if not chunk:
                return False
            for byte in chunk:
                # Check for null bytes (0x00), which are common in binary files
                if byte == 0:
                    return True
        except Exception as e:
            print(f"Error calling `is_binary` on file {self.name}: {e!r}")
            return False
        return False

    @property
    def content(self) -> list[Any]:
        """Helper for self.read()."""
        print(f"\033[33mWARNING\033[0m - Depreciated function <{self.__class__.__name__}.content>")
        if not self._content:
            # self._content = self.read()
            self._content = self.read_text().splitlines()
        return self._content

    def _read_chunk(self, size=4096) -> bytes:
        """Read a chunk of the file and return it as bytes."""
        with open(self.path, "rb") as f:
            return f.read(size)

    def md5_checksum(self, size=4096) -> str:
        """Return the MD5 checksum of a portion of the image file."""
        data = self._read_chunk(size)
        return hashlib.md5(data).hexdigest()

    @property
    def is_executable(self) -> bool:
        """Check if the file has the executable bit set."""
        return os.access(self.path, os.X_OK)

    @property
    def is_gitobject(self) -> bool:
        """Check if the file is a git object."""
        return GIT_OBJECT_REGEX.match(self.name) is not None

    @property
    def is_image(self) -> bool:
        """Check if the file is an image."""
        return self.suffix.lower() in FILE_TYPES["img"]

    @property
    def is_video(self) -> bool:
        """Check if the file is a video."""
        return all((self.suffix.lower() in FILE_TYPES["video"], self.__class__.__name__ == "Video"))

    def detect_encoding(self) -> str:
        """Detect encoding of the file."""
        self.encoding = chardet.detect(self._read_chunk(2048))["encoding"] or self.encoding
        return self.encoding

    def sha256(self) -> str:
        """Return a reproducable sha256 hash of the file."""
        serialized_object = pickle.dumps({"md5": self.md5_checksum(), "size": self.size})
        return hashlib.sha256(serialized_object).hexdigest()

    def __hash__(self) -> int:
        return hash(self.sha256())
        # return hash((self.md5_checksum(), self.size))

    def __iter__(self) -> Iterator[str]:
        """Iterate over the lines of a file."""
        if self.content is not None:
            try:
                for line in self.content:
                    yield str(line).strip()
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

        Parameters
        ----------
            item (str): The line to check for

        """
        return any(item in line for line in self) or any(
            item in word for word in item.split(" ") for line in self
        )

    def __eq__(self, other: "File", /) -> bool:
        """Compare two FileObjects.

        Paramaters
        ----------
            other (Object): The Object to compare (FileObject, VideoObject, etc.)

        """
        return all((other.exists, self.exists, hash(self) == hash(other)))

    def __bool__(self) -> bool:
        """Check if the file exists."""
        return bool(super().exists)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name}, encoding={self.encoding}, size={self.size_human})".format(
            **vars(self)
        )

    # def __init_subclass__(cls) -> None:
    #     return super().__init_subclass__()
