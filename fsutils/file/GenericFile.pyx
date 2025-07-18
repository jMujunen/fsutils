"""Base class and building block for all other classes defined in this library."""

cimport cython
import os
from typing import Iterator, Any
import json
import re
from datetime import datetime
from pathlib import Path
from fsutils.utils.mimecfg import FILE_TYPES
from fsutils.utils.tools import format_bytes

from collections import namedtuple
from typing import TypeAlias

times: TypeAlias = namedtuple("st_times", ["atime", "mtime", "ctime"])

GIT_OBJECT_REGEX = re.compile(r"([a-f0-9]{37,41})")




cdef class Base:
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

    def __cinit__(self, str path, str encoding="utf-8") -> None:
        """Construct the Base object."""
        self.path = path
        self.encoding = encoding

    def __init__(self, str path, str encoding="utf-8") -> None:
        """Construct the Base object.

        Paramaters:
        ----------
            - `path (str)` : The path to the file
            - `encoding (str)` : Encoding type of the file (default is utf-8)
        """
        try:
            self.path = os.path.abspath(os.path.expanduser(str(path)))
            self.encoding = encoding
            if not os.path.exists(self.path):
                raise FileNotFoundError(f"File '{path}' does not exist")
        except PermissionError as e:
            print(f"Permission denied to access file {self.name}: {e!r}")

    def head(self, unsigned int n = 5) -> list[str]:
        """Return the first n lines of the file."""
        content = (line for line in self.read_text().splitlines())
        head = []
        for _ in range(n):
            try:
                head.append(next(content))
            except StopIteration:
                break
        return head
    def tail(self, int n = 5) -> list[str]:
        """Return the last n lines of the file."""
        return self.read_text().splitlines()[-n:]

    def stat(self) -> os.stat_result:
        """Call os.stat() on the file path."""
        return os.stat(self.path)

    @property
    def name(self) -> str:
        """Return the file name with extension."""
        return os.path.basename(self.path)

    @property
    def parent(self) -> str:
        """Return the parent directory path of the file."""
        return os.path.dirname(self.path)

    @property
    def size_human(self) -> str:
        """Return the size of the file in human readable format."""
        return format_bytes(self.size)

    @property
    def size(self) -> int:
        """Return the size of the file in bytes."""
        return int(self.stat().st_size)

    @property
    def prefix(self) -> str:
        """Return the file name without extension."""
        stem, _ = os.path.splitext(self.name)
        return stem

    @property
    def suffix(self):
        """Return the file extension."""
        cdef str _, suffix
        _, suffix = os.path.splitext(self.path)
        return suffix
    @suffix.setter
    def  suffix(self, str value) -> None:
        """Set the file extension."""
        self._suffix = value

    def is_binary(self) -> bool:
        """Check for null bytes in the file contents, telling us its binary data."""
        cdef bytes chunk
        cdef unsigned int byte
        try:
            chunk = self._read_chunk(1024)
            if not chunk:
                return False
            for byte in chunk:
                # Check for null bytes (0x00), which are common in binary files
                if byte == 0:
                    return True
        except Exception as e:
            print(f"Error calling `is_binary()` on file {self.name}: {e!r}")
            return False
        return False

    def is_gitobject(self) -> bool:
        """Check if the file is a git object."""
        return GIT_OBJECT_REGEX.match(self.name) is not None

    def is_image(self) -> bool:
        """Check if the file is an image."""
        return self.suffix.lower() in FILE_TYPES["img"]

    def is_video(self) -> bool:
        """Check if the file is a video."""
        return all((self.suffix.lower() in FILE_TYPES["video"], self.__class__.__name__ == "Video"))
    @property
    def mtime(self) -> datetime:
        """Return the last modification time of the file."""
        return datetime.fromtimestamp(self.stat().st_mtime)
    @property
    def ctime(self) -> datetime:
        """Return the last metadata change of the file."""
        return datetime.fromtimestamp(self.stat().st_ctime)
    @property
    def atime(self)  -> datetime:
        """Return the last access time of the file."""
        return datetime.fromtimestamp(self.stat().st_atime)

    def times(self) -> times: #:tuple[datetime, datetime, datetime]:
        """Return access, modification, and creation times of a file."""
        a, m, c = map(datetime.fromtimestamp, self.stat()[-3:])
        return times(m, c, a)
    @property
    def parts(self) -> tuple[str, ...]:
        return Path(self.path).parts

    def exists(self) -> bool:
        """Check if the file exists."""
        return os.path.exists(self.path) # type: ignore

    def __iter__(self) -> Iterator[str|bytes]:
        """Iterate over the lines of a file."""
        if self.is_binary():
            with open(self.path, 'rb') as f:
                yield from f
        else:
            with open(self.path, 'r', encoding=self.encoding) as f:
                yield from f
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
        return any(item in line for line in self) # type: ignore

    def __eq__(self, Base other, /) -> bool:
        """Compare two FileObjects.

        Paramaters
        ----------
            other (Object): The Object to compare (FileObject, VideoObject, etc.)

        """
        return self.sha256() == other.sha256()

    def __bool__(self) -> bool:
        """Check if the file exists."""
        return self.exists()

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name}, encoding={self.encoding}, size={self.size_human}"

    def _read_chunk(self, chunk_size: int = 16384) -> bytes:
        """Read a chunk of the file.

        Args:
        -----
           chunk_size (int): The size of the chunk to read. Defaults to 16384 bytes.
        Returns:
        --------
           bytes: The chunk of data read from the file.
        """
        with open(self.path, 'rb') as f:
            return f.read(chunk_size)

    def read_text(self) -> str:
        """Read the contents of the file as a string."""
        with open(self.path, 'r', encoding=self.encoding) as f:
            return f.read()

    def sha256(self) -> str:
        """Compute and return the SHA-256 hash of the file."""
        cdef bytes _path = self.path.encode('utf-8')
        cdef char* path = <char*>_path
        cdef sha256_hash_t *hash = <sha256_hash_t *>returnHash(path)
        if hash != NULL:
            return ''.join(format(hash._hash[x], '02x') for x in range(0,32))
        else:
            raise ValueError("Failed to compute SHA256 hash for file: {}".format(self.path))


    def read_json(self) -> dict:
        return json.loads(self.read_text())

    def __hash__(self) -> int:
        """Return the hash of the file."""
        return hash(self.sha256())
    def __str__(self) -> str:
        """Return a string representation of the file."""
        return self.path

