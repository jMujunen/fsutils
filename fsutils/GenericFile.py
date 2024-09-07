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
class FileMetaData:
    """This class holds metadata about a file"""

    path: str


class File:
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

    _content: list[Any] = []

    def __init__(self, path: str, encoding: str = "utf-8") -> None:
        """Constructor for the FileObject class.

        Paramaters:
        ----------
            - `path (str)` : The path to the file
            - `encoding (str)` : Encoding type of the file (default is utf-8)
        """
        self.encoding = encoding
        self.path = os.path.abspath(os.path.expanduser(path))
        self._exsits = self.exists
        # self._content = []
        # print(f"{self.__class__.__name__}(exists={self.exists}, basename={self.basename})")
        # print(self.__doc__)

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
    def is_link(self) -> bool:
        """Check if the path is a symbolic link."""
        return os.path.islink(self.path)

    @property
    def size_human(self) -> str:
        """Return the size of the file in human readable format."""
        return str(Size(self.size))

    @property
    def size(self) -> int:
        """Return the size of the file in bytes."""
        return int(os.path.getsize(self.path))

    @property
    def dir_name(self) -> str:
        """Return the parent directory of the file."""
        return os.path.dirname(self.path) if not self.is_dir else self.path

    @property
    def file_name(self) -> str:
        """Return the file name without the extension."""
        return str(os.path.splitext(self.path)[0])

    @property
    def filename(self) -> str:
        """Return the file name with the extension."""
        return str(os.path.basename(self.path))

    @property
    def extension(self) -> str:
        """Return the file extension."""
        return str(os.path.splitext(self.path)[-1]).lower()

    @extension.setter
    def extension(self, ext: str) -> int:
        """Set a new extension to the file."""
        new_path = os.path.splitext(self.path)[0] + ext
        try:
            shutil.move(self.path, new_path, copy_function=shutil.copy2)
        except OSError as e:
            print(f"Error while saving {self.filename}: {e}")
            return 1
        return 0

    @property
    def exists(self) -> bool:
        return os.path.exists(self.path)

    @property
    def content(self) -> list[Any]:
        """Helper for self.read()."""
        if not self._content:
            self._content = self.read()
        return self._content

    def read(self, *args: Any) -> list[Any]:
        """Read the content of a file.

        While this method is cabable of reading certain binary data, it would be good
        practice to override this method in subclasses that deal with binary files.

        args:
        ------------
            - `int, int` : Return lines content[x:y]
        Returns:
        ----------
            str: The content of the file
        """
        x, y = None, None
        if len(args) == 2:
            # Define list slice
            x, y = args
            try:
                with open(self.path, "rb") as f:
                    lines = f.read().decode(self.encoding).split("\n")
                    self._content = list(lines[x:y])

            except UnicodeDecodeError as e:
                print(f"{e!r}: {self.filename} could not be decoded as {self.encoding}")
            except Exception:
                print(f"Reading of type {self.__class__.__name__} is unsupported")
        return self._content

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
    def is_file(self) -> bool:
        """Check if the object is a file."""
        if GIT_OBJECT_REGEX.match(self.filename):
            return False
        return os.path.isfile(self.path)

    @property
    def is_executable(self) -> bool:
        """Check if the file has the executable bit set."""
        return os.access(self.path, os.X_OK)

    @property
    def is_dir(self) -> bool:
        """Check if the object is a directory""."""
        return os.path.isdir(self.path)

    @property
    def is_video(self) -> bool:
        """Check if the file is a video."""
        return self.extension.lower() in FILE_TYPES["video"]

    @property
    def is_gitobject(self) -> bool:
        """Check if the file is a git object."""
        return GIT_OBJECT_REGEX.match(self.filename) is not None

    @property
    def is_image(self) -> bool:
        """Check if the file is an image."""
        return self.extension.lower() in FILE_TYPES["img"]

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
        """Detects encoding of the file."""
        with open(self.path, "rb") as f:
            return chardet.detect(f.read())["encoding"]

    # def unixify(self) -> List[str]:
    #     """Convert DOS line endings to UNIX - \\r\\n -> \\n"""
    #     self._content = "".split(re.sub(r"\r\n$|\r$", "\n", "".join(self.content)))
    #     return self._content

    def __hash__(self) -> int:
        try:
            return hash(("\n".join(self.content), self.size))
        except TypeError:
            return hash((self.md5_checksum, self.size))

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

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(size={self.size_human}, path={self.path}, basename={self.filename}, extension={self.extension})".format(
            **vars(self)
        )

    def __str__(self) -> str:
        try:
            return "\n".join(self.content)
        except TypeError:
            return self.__repr__()

    # def __getattribute__(self, name: str, /) -> Any:
    # """Get an attribute of the File Object"""
    # return self.__dict__.get(name, None)
