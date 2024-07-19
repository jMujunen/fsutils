"""DirNode.Dir -  Represents a directory. Contains methods to list objects inside this directory."""

import os
import datetime
import re
from typing import List, Iterator, Any, Union
# from fsutils import File, Log, Exe, Video, Img
from .GenericFile import File
from .LogFile import Log
from .ScriptFile import Exe
from .VideoFile import Video
from .ImageFile import Img
from .GitObject import Git
from size import Converter


class Dir(File):
    """
    A class representing information about a directory.

    Attributes:
    ----------
        path (str): The path to the directory (Required)
        _files (list): A list of file names in the directory
        _directories (list): A list containing the paths of subdirectories
        _objects (list): A list of items in the directory represented by FileObject

    Methods:
    ----------
        file_info (file_name): Returns information about a specific file in the directory
        objects (): Convert each file in self to an appropriate type of object inheriting from FileObject
        getinfo (): Returns a list of extentions and their count
        __eq__ (other): Compare properties of two DirectoryObjects
        __contains__ (other): Check if an item is present in two DirectoryObjects
        __len__ (): Return the number of items in the object
        __iter__ (): Define an iterator which yields the appropriate instance of FileObject
    Properties:
    ----------
        files       : A read-only property returning a list of file names
        objects     : A read-only property yielding a sequence of DirectoryObject or FileObject instances
        directories : A read-only property yielding a list of absolute paths for subdirectories

    """

    def __init__(self, path: str):
        self._files = []
        self._directories = []
        self._objects = []
        super().__init__(path)

    @property
    def files(self) -> List[str]:
        """Return a list of file names in the directory represented by this object."""
        return [f.basename for f in self if not os.path.isdir(f.path)]

    @property
    def file_objects(self) -> List[Union[File, Exe, Log, Img, Video, Git]]:
        return [item for item in self if isinstance(item,
                                                    (File, Exe, Log, Img, Video, Git)
            )]
    @property
    def content(self) -> List[Any] | None:
        try:
            return os.listdir(self.path)
        except NotADirectoryError:
            pass

    # @property
    # def directories(self) -> List[str]:
    #     """Return a list of subdirectory paths in the directory represented by this object."""
    #     raise NotImplementedError("Depreciated method!")

    @property
    def rel_directories(self) -> List[str]:
        """Return a list of subdirectory paths relative to the directory represented by this object"""
        return [f".{folder.path.replace(self.path, "")}" for folder in self.dirs]

    def objects(self) -> List[File | Exe | Log | Img | Video | Git]:
        """Return a list of fsutil objects inside self"""
        if self._objects is None:
            self._objects = [file for file in self]
        return self._objects

    def file_info(self, file_name: str) -> File | None:
        """
        Query the object for files with the given name.
        Returns an appropriate FileObject if found.

        Parameters
        ----------
            file_name (str): The name of the file

        Returns:
        ---------
            File (class) | None: Information about the specified file if found
        """
        try:
            try:
                if file_name in os.listdir(self.path):
                    return obj(os.path.join(self.path, file_name))
            except (NotADirectoryError, FileNotFoundError):
                pass
            for d in self.dirs:
                content = os.listdir(os.path.join(self.path, d.path))
                if file_name in content:
                    return obj(os.path.join(self.path, d.path, file_name))
                # return obj(os.path.join(self.path, d, file_name))
        except (FileNotFoundError, NotADirectoryError) as e:
            print(e)
        return

    @property
    def is_dir(self) -> bool:
        return os.path.isdir(self.path)

    @property
    def is_empty(self) -> bool:
        """Check if the directory is empty.

        Returns:
        --------
            bool: True if the directory is empty, False otherwise
        """
        return len(self.files) == 0

    @property
    def images(self) -> List[Img]:
        """Return a list of ImageObject instances found in the directory.

        Returns:
        --------
            List[ImageObject]: A list of ImageObject instances
        """
        return [item for item in self if isinstance(item, Img)]

    @property
    def videos(self) -> List[Video]:
        """Return a list of VideoObject instances found in the directory."""
        return [item for item in self if isinstance(item, Video)]

    @property
    def dirs(self) -> List[File]:
        """Return a list of DirectoryObject instances found in the directory."""
        return [item for item in self if isinstance(item, Dir)]

    def getinfo(self, path: str) -> dict:
        """Return information about a file or directory."""
        raise NotImplementedError("Not implemented yet")
        return {}

    def sort(self, spec="mtime", reversed=True) -> None:
        """Sort the files and directories by the specifying attribute."""
        specs = {
            "mtime": lambda: file_stats.st_mtime,
            "ctime": lambda: file_stats.st_ctime,
            "atime": lambda: file_stats.st_atime,
            "size": lambda: int(Converter(file_stats.st_size)),
            "name": lambda: print(self.basename),
            "ext": lambda: print(self.extension),
        }
        files = []
        for item in self:
            if item.is_file and spec in list(specs.keys())[:4]:
                file_stats = os.stat(item.path)
                result = datetime.datetime.fromtimestamp(specs[spec]()).strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
                files.append((item.path, result))
            else:  # item.is_file and spec in ["ext", "name"]:
                result = specs[spec]()
        files.sort(key=lambda x: x[1])
        files.reverse()
        # Print the table
        print(("{:<20}{:<40}").format(spec, "File"))
        for filepath, s in files:
            print(("{:<20}{:<40}").format(s, filepath.replace(self.path, "")))

    def __contains__(self, item: File) -> bool:
        """Compare items in two DirectoryObjects

        Parameters:
        ----------
            item (FileObject, VideoObject, ImageObject, ExecutableObject, DirectoryObject): The item to check.

        Returns:
        ----------
            bool: True if the item is present, False otherwise.
        """
        if isinstance(item, (File, Video, Img, Exe, Dir)):
            return item.basename in self.files
        return item in self.files

    def __len__(self):
        """Return the number of items in the object"""
        return len([i for i in self.objects()])

    def __iter__(self) -> Iterator[File | Exe | Log | Img | Video | Git]:
        """Yield a sequence of File instances for each item in self"""
        for root, _, files in os.walk(self.path):
            for file in files:
                path = os.path.join(root, file)  # full path of the file
                if os.path.isdir(path):
                    yield Dir(path)
                else:
                    yield obj(path)
            for directory in _:
                yield Dir(os.path.join(root, directory))

    def __eq__(self, other: "Dir") -> bool:
        """Compare the contents of Dirs

        Parameters:
        ----------
            other (class): The class instance to compare with.

        Returns:
        ----------
            bool: True if the path of the two instances are equal, False otherwise.
        """
        return self.content == other.content

    def fmt(self, *args) -> str:
        """Print a formatted string representation of each object in self."""
        return f"{self.__class__.__name__}({self.path})"

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(size={self.size}, dir_name={self.path}, path={self.path}, is_empty={self.is_empty})".format(
            **vars(self)
        )


def obj(path: str) -> File:
    """
    Create an object of the appropriate class, based on the extension of the file.

    Parameters:
    ----------
        path (str): Path of the file or directory.

    Returns:
    ---------
        A subclass of `File`, which can be one of the following classes - Img, Log, Video, Exe, Dir.

    Raises:
    -------
        ValueError: If path is None.
        FileNotFoundError: If provided path does not exist.

    """
    if not path or not isinstance(path, str):
        raise ValueError("Path cannot be None")
    if not os.path.exists(path):
        # pass
        raise FileNotFoundError(path, " does not exist")
    ext = os.path.splitext(path)[1].lower()
    classes = {
        # Images
        ".jpg": Img,
        ".jpeg": Img,
        ".png": Img,
        ".nef": Img,
        # ".heic": Img,
        ".gif": Img,
        # Logs
        ".log": Log,
        ".csv": Log,
        # Videos
        ".mp4": Video,
        ".avi": Video,
        ".mkv": Video,
        ".wmv": Video,
        ".webm": Video,
        ".mov": Video,
        # Code
        ".py": Exe,
        ".bat": Exe,
        ".sh": Exe,
        # Directories
        "": Dir,
    }
    others = {
        re.compile(r"(\d+mhz|\d\.\d+v)"): Log,
        re.compile(r"([a-f0-9]{37,41})"): Git
    }

    cls = classes.get(ext)
    if not cls:
        for k, v in others.items():
            if k.match(path.split(os.sep)[-1]):
                return v(path)
        return File(path)
    return cls(path)


if __name__ == "__main__":
    path = Dir("/home/joona/.dotfiles")
    from ExecutionTimer import ExecutionTimer

    with ExecutionTimer():
        for item in path:
            if item.is_dir:
                print(item)
