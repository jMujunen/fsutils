"""Base class and building block for all other classes defined in this library."""

import hashlib
import os
import pickle
import re
import shutil
from collections.abc import Iterator
from typing import Any

import chardet
from size import Size

from mimecfg import FILE_TYPES

GIT_OBJECT_REGEX = re.compile(r"([a-f0-9]{37,41})")


class File:
    """This is the base class for all of the following objects.

    It represents a generic file and defines the common methods that are used by all of them.

    It can be used standlone (Eg. text based files) or as a parent class for other classes.

    Attributes
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

    Methods
    ----------
        - `read()` : Return the contents of the file
        - `head(self, n=5)` : Return the first n lines of the file
        - `tail(self, n=5)` : Return the last n lines of the file
        - `detect_encoding()` : Return the encoding of the file based on its content
        - `__eq__()` : Compare properties of FileObjects
        - `__str__()` : Return a string representation of the object

    """

    _basename: str

    def __init__(self, path: str, encoding="utf-8") -> None:
        """Construct the FileObject object.

        Paramaters:
        ----------
            - `path (str)` : The path to the file
            - `encoding (str)` : Encoding type of the file (default is utf-8)
        """
        self.path = os.path.abspath(os.path.expanduser(path))
        self.encoding = encoding
        self.exists = os.path.exists(self.path)
        if not self.exists:
            raise FileNotFoundError(f"File '{self.path}' does not exist")
        self._content = []

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
    def dir_path(self) -> str:
        """Return the parent directory of the file."""
        return os.path.dirname(self.path) if not self.is_dir else self.path

    @property
    def dir_name(self) -> str:
        """Depreciated, use dir_path instead."""
        print("\033[1;4;93m[WARNING]\033[0m - 'dir_name' is deprecated. Use 'dir_path' instead.")
        return self.dir_path

    @property
    def dir(self) -> str:
        """Return the parent folder name."""
        return self.path.split(os.sep)[-2]

    @property
    def basename(self) -> str:
        """Return the file name with the extension."""
        return str(os.path.basename(self.path))

    @property
    def prefix(self) -> str:
        """Return the file name without extension."""
        return os.path.splitext(self.basename)[0]

    @basename.setter
    def basename(self, name: str) -> str:
        """Set a new name for the file."""
        new_path = os.path.join(self.dir_path, name)
        if os.path.exists(new_path):
            raise FileExistsError("A file with this name already exists.")
        os.rename(self.path, new_path)
        self.__setattr__("basename", name)
        self.__setattr__("path", new_path)
        self.__setattr__("dir_path", os.path.dirname(new_path))
        return self.basename

    @property
    def extension(self) -> str:
        """Return the file extension."""
        return str(os.path.splitext(self.path)[-1]).lower()

    @extension.setter
    def extension(self, ext: str) -> "File":
        """Set a new extension to the file."""
        new_path = os.path.splitext(self.path)[0] + ext
        try:
            shutil.move(self.path, new_path, copy_function=shutil.copy2)
            self.__setattr__("path", new_path)
        except OSError as e:
            print(f"Error while saving {self.basename}: {e}")
        return self

    @property
    def is_binary(self) -> bool:
        """Check for null bytes in the file contents, telling us its binary data."""
        try:
            with open(self.path, "rb") as file:
                while True:
                    chunk = file.read(1024)
                    if not chunk:
                        break
                    for byte in chunk:
                        # Check for null bytes (0x00), which are common in binary files
                        if byte == 0:
                            return True
        except Exception as e:
            print(f"Error calling `is_binary` on file {self.basename}: {e!r}")
            return False
        return False

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

        Args:
        ------
            - tuple(int, int) : (optional) specify indices to slice the content list.
        """
        _ = self.detect_encoding()
        if self.is_binary:
            return []
        if _ is not None:
            self.encoding = _
        try:
            x, y = args
        except ValueError:
            x, y = None, None
        try:
            with open(self.path, "rb") as f:
                lines = f.read().decode(self.encoding).split("\n")
                self._content = list(lines[x:y])
        except UnicodeDecodeError:
            print(f"{self.basename} could not be decoded as {self.encoding}")
        except Exception as e:
            print(f"Reading of type {self.__class__.__name__} is unsupported [{e!r}]")
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
    def is_file(self) -> bool:
        """Check if the object is a file."""
        if GIT_OBJECT_REGEX.match(self.basename):
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
        return GIT_OBJECT_REGEX.match(self.basename) is not None

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
        """Detect encoding of the file."""
        with open(self.path, "rb") as f:
            return chardet.detect(f.read())["encoding"]

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

        Paramaters:
        -----------
            other (Object): The Object to compare (FileObject, VideoObject, etc.)

        """
        return all((other.exists, self.exists, hash(self) == hash(other)))

    def __bool__(self) -> bool:
        """Check if the file exists."""
        return self.exists

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(size={self.size_human}, name={self.basename}, ext={self.extension})".format(
            **vars(self)
        )
