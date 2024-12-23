"""Base class and building block for all other classes defined in this library."""

import hashlib
import os
import pickle
import re
from collections.abc import Iterator
from datetime import datetime
import json
from pathlib import Path
from typing import Any, Type
import chardet
from fsutils.utils.mimecfg import FILE_TYPES
from fsutils.utils.tools import format_bytes
from collections import namedtuple

from libc.stdlib cimport free, malloc, realloc


GIT_OBJECT_REGEX = re.compile(r"([a-f0-9]{37,41})")

ctypedef tuple[datetime, datetime, datetime] DatetimeTuple
cdef St = namedtuple('St',['atime', 'mtime', 'ctime'])

cdef extern from "stdio.h":
    ctypedef ssize_t ssize_ts
    ctypedef size_t size_t
    ctypedef int FILE

    cdef FILE* fopen(const char* filename, const char* mode)
    ssize_t fread(void* ptr, size_t size, size_t nmemb, FILE* stream)
    int fclose(FILE* stream)


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
        try:
            if isinstance(path, str):
                path = Path(path)
            self.path = os.path.abspath(os.path.expanduser(str(path)))
            self.encoding = encoding
            if not os.path.exists(path):
                raise FileNotFoundError(f"File '{path}' does not exist")
            super().__init__(self.path, *args, **kwargs) # type: ignore
        except PermissionError as e:
            print(f"Permission denied to access file {self.name}: {e!r}")

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
        return format_bytes(self.size)

    @property
    def size(self) -> int:
        """Return the size of the file in bytes."""
        return int(self.stat().st_size)

    @property
    def prefix(self) -> str:
        """Return the file name without extension."""
        return self.stem

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

    @property
    def content(self) -> list[str]:
        """Helper for self.read()."""
        print(f"\033[33mWARNING\033[0m - Depreciated function <{self.__class__.__name__}.content>")
        return self.read_text().splitlines()


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
    def atime(self) -> datetime:
        """Return the last access time of the file."""
        return datetime.fromtimestamp(self.stat().st_atime)

    def times(self) -> DatetimeTuple:
        """Get the modification, access and creation times of a file."""
        a, m, c = self.stat()[-3:]
        self.st = St(datetime.fromtimestamp(m), datetime.fromtimestamp(a), datetime.fromtimestamp(c))
        return self.st


    def __iter__(self) -> Iterator[str|bytes]:
        """Iterate over the lines of a file."""
        if self.is_binary():
            with self.open('rb') as f:
                yield from f
        else:
            with self.open('r', encoding=self.encoding) as f:
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
        return any(item in line for line in self)

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

    def detect_encoding(self) -> str:
        """Detect encoding of the file."""
        cdef unsigned short int chunk_size = 2048
        cdef str encoding = chardet.detect(self._read_chunk(chunk_size))["encoding"] or self.encoding
        if encoding == 'ascii':
            encoding = 'utf-8'
        return encoding


    def md5_checksum(self, chunk_size=16384) -> str:
        """
        Calculate the MD5 checksum of the file from the specified chunk.

        Parameters
        ----------
            chunk_size : int, optional (default=16384)

        """
        return hashlib.md5(self._read_chunk(chunk_size)).hexdigest()


    def sha256(self, unsigned int chunk_size=16384) -> str:
        """Return a reproducible sha256 hash of the file."""
        cdef str md5  = self.md5_checksum(chunk_size)
        cdef bytes serialized_object = pickle.dumps({"md5": md5, "size": self.size})
        return hashlib.sha256(serialized_object).hexdigest()
    def read_json(self)-> dict|list:
        return json.loads(self.read_text())

    def _read_chunk(self, unsigned int size=16384, str spec='c') -> bytes:
        """Read a chunk of the file and return it as bytes."""
        if spec == 'c':
            return c_read_chunk(self,  size)
        else:
            with self.open('rb', encoding=self.encoding) as f:
                return f.read(size)

    def __hash__(self) -> int:
        """Return the hash of the file."""
        return hash(self.sha256())


cdef c_read_chunk(self, unsigned int size=16384):
    """Read a chunk of data from the file."""
    cdef char* buffer
    cdef ssize_t bytes_read
    cdef FILE* fptr

    # Allocate memory for the buffer
    buffer = <char*>malloc(size * sizeof(char)) # type: ignore
    if not buffer:
        raise MemoryError("Failed to allocate memory for buffer")

    try:
        # Open the file in binary read mode
        fptr = fopen(self.path.encode('utf-8'), 'rb'.encode('utf-8'))# type: ignore
        if not fptr:
            raise IOError(f"Failed to open file: {self.path}")

        try:
            # Read data into the buffer
            bytes_read = fread(buffer, 1, size, fptr)# type: ignore
            if bytes_read < 0:# type: ignore
                raise IOError("Error reading from file")

            # Convert the buffer to a Python bytes object and return it
            return bytes(buffer[:bytes_read]) # type: ignore
        finally:
            # Close the file
            fclose(fptr)
    finally:
        # Free the allocated memory for the buffer
        free(buffer) # type: ignore


