"""Base class and building block for all other classes defined in this library"""

import os
import re
import shutil
import chardet
from typing import Iterator, List, Any
from fsutils.mimecfg import FILE_TYPES

GIT_OBJECT_REGEX = re.compile(r"([a-f0-9]{37,41})")


class File:
    """
    This is the base class for all of the following objects.
    It represents a generic file and defines the common methods that are used by all of them.
    It can be used standlone (Eg. text based files) or as a parent class for other classes.

    Attributes:
    ----------
        encoding (str): The encoding to use when reading/writing the file. Defaults to utf-8.
        path (str): The absolute path to the file.
        content (Any): Contains the content of the file. Only holds a value if read() is called.

    Properties:
    ----------
        size: The size of the file in bytes.
        file_name: The name of the file without its extension.
        extension: The extension of the file (Eg. file.out.txt -> file.out)
        basename: The basename of the file (Eg. file.out.txt)
        is_file: Check if the objects path is a file
        is_executable: Check if the object has an executable flag
        is_image: Check if item is an image
        is_video: Check if item is a video
        is_gitobject: Check if item is a git object
        is_link: Check if item is a symbolic link
        content: The content of the file. Only holds a value if read() is called.

    Methods:
    ----------
        read(): Return the contents of the file
        head(self, n=5): Return the first n lines of the file
        tail(self, n=5): Return the last n lines of the file
        detect_encoding(): Return the encoding of the file based on its content
        __eq__(): Compare properties of FileObjects
        __str__(): Return a string representation of the object

    """

    def __init__(self, path: str, encoding: str = "utf-8") -> None:
        """
        Constructor for the FileObject class.

        Paramaters:
        ----------
            path (str): The path to the file
            encoding (str): Encoding type of the file (default is utf-8)
        """
        self.encoding = encoding
        self.path = os.path.abspath(os.path.expanduser(path))
        self._content = []

    def head(self, n=5) -> list:
        """
        Return the first n lines of the file

        Paramaters:
        ----------
            n (int): The number of lines to return (default is 5)

        Returns:
        ----------
            list: The first n lines of the file
        """
        # if isinstance(self, (File, Exe, Log)):
        if self.content is not None:
            try:
                return self.content[:n]
            except Exception as e:
                raise TypeError(f"P{e}: The object must be a File or an Exe instance")
        return []
    def tail(self, n=5) -> list:
        """
        Return the last n lines of the file

        Paramaters:
        ----------
            n (int): The number of lines to return (default is 5)

        Returns:
        ----------
            list: The last n lines of the file
        """
        # if isinstance(self, (File, Exe)):
        if self.content is not None:
            try:
                return self.content[-n:]
            except Exception as e:
                raise TypeError(f"{e}: The object must be a FileObject or an ExecutableObject")
        return []

    @property
    def is_link(self) -> bool:
        """Check if the path is a symbolic link."""
        return os.path.islink(self.path)

    @property
    def size(self) -> int:
        """Return the size of the file in bytes"""
        return int(os.path.getsize(self.path))

    @property
    def dir_name(self) -> str:
        """Return the parent directory of the file"""
        return os.path.dirname(self.path) if not self.is_dir else self.path

    @property
    def file_name(self) -> str:
        """Return the file name without the extension"""
        return str(os.path.splitext(self.path)[0])

    @property
    def basename(self) -> str:
        """Return the file name with the extension"""
        return str(os.path.basename(self.path))

    @property
    def extension(self) -> str:
        """Return the file extension"""
        return str(os.path.splitext(self.path)[-1]).lower()

    @extension.setter
    def extension(self, ext: str) -> int:
        """Set a new extension to the file"""
        new_path = os.path.splitext(self.path)[0] + ext
        try:
            shutil.move(self.path, new_path, copy_function=shutil.copy2)
        except IOError as e:
            print(f"Error while saving {self.basename}: {e}")
            return 1
        return 0

    @property
    def content(self) -> List[Any] | None:
        """Helper for self.read()"""
        if not self._content:
            self._content = self.read()
        return self._content

    def read(self, **kwargs) -> List[Any]:
        """Method for reading the content of a file.

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
                    lines = f.read().decode(self.encoding)
                    content = list(
                        lines.split("\n")[kwargs.get("a", 0) : kwargs.get("b", len(self._content))]
                    )
            except Exception as e:
                # print(e)
                try:
                    with open(self.path, "r", encoding=self.encoding) as f:
                        content = f.readlines()
                except Exception as e:
                    print(e)
                    try:
                        with open(self.path, "rb") as f:
                            content = f.readlines()
                    except Exception as e:
                        raise TypeError(f"Reading {type(self)} is unsupported")
            self._content = content
        return (
            self._content[kwargs.get("a", 0) : kwargs.get("b", len(self._content))]
            if kwargs
            else self._content
        )

    @property
    def is_file(self) -> bool:
        """Check if the object is a file"""
        if GIT_OBJECT_REGEX.match(self.basename):
            return False
        return os.path.isfile(self.path)

    @property
    def is_executable(self) -> bool:
        """Check if the file has the executable bit set"""
        return os.access(self.path, os.X_OK)

    @property
    def is_dir(self) -> bool:
        """Check if the object is a directory"" """
        return os.path.isdir(self.path)

    @property
    def is_video(self) -> bool:
        """Check if the file is a video"""
        return self.extension.lower() in FILE_TYPES["video"]

    @property
    def is_gitobject(self) -> bool:
        """Check if the file is a git object"""
        return GIT_OBJECT_REGEX.match(self.basename) is not None

    @property
    def is_image(self) -> bool:
        """Check if the file is an image"""
        return self.extension.lower() in FILE_TYPES["img"]

    def detect_encoding(self) -> str | None:
        """Detects encoding of the file"""
        with open(self.path, "rb") as f:
            encoding = chardet.detect(f.read())["encoding"]
        return encoding

    def unixify(self) -> List[str]:
        """Convert DOS line endings to UNIX - \\r\\n -> \\n"""
        self._content = "".split(re.sub(r"\r\n$|\r$", "\n", "".join(self.content)))
        return self._content

    def __iter__(self) -> Iterator[str]:
        """Iterate over the lines of a file.

        Yields:
        --------
            str: A line from the file
        """
        if self.content is not None:
            try:
                for line in self.content:
                    yield (str(line).strip())
            except TypeError as e:
                # else:
                raise TypeError(f"Object of type {type(self)} is not iterable: {e}")

    def __len__(self) -> int:
        """Get the number of lines in a file."""
        try:
            return len(list(iter(self)))
        except Exception as e:
            raise TypeError(f"Object of type {type(self)} does not support len(): {e}")

    def __contains__(self, item: Any) -> bool:
        """Check if a line exists in the file.

        Parameters:
        ----------
            item (str): The line to check for

        """
        return any(item in line for line in self) or any(
            item in word for word in item.split(" ") for line in self
        )

    def __eq__(self, other) -> bool:
        """Compare two FileObjects

        Paramaters:
        ----------
            other (Object): The Object to compare (FileObject, VideoObject, etc.)
        """
        if not isinstance(other, (self.__class__, File)):
            return False
        try:
            self._content = self.read()
        except TypeError:
            print(f"Error: {type(other)} is unsupported")
        return self._content == other.content

    def __str__(self) -> str:
        """Return a string representation of the FileObject"""
        return str(self.__dict__)

    def __setattr__(self, name: str, value: Any, /) -> None:
        """Set an attribute for the FileObject."""
        if name == "_File__path":
            raise AttributeError("Cannot change file path.")
        self.__dict__[name] = value

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(size={self.size}, path={self.path}, basename={self.basename}, extension={self.extension})".format(
            **vars(self)
        )


if __name__ == "__main__":
    readme = File("~/.dotfiles/README.md")
    print(readme == readme)
