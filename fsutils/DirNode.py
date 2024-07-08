"""DirNode.Dir -  Represents a directory. Contains methods to list objects inside this directory."""

import os
import datetime
import re
from typing import List, Iterator
from dataclasses import dataclass
from fsutils import File, Log, Exe, Video, Img


@dataclass
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
        self._files = None
        self._directories = None
        self._objects = None
        super().__init__(path)

    @property
    def files(self) -> List[File]:
        """
        Return a list of file names in the directory represented by this object.

        Returns:
        ----------
            list: A list of file names
        """
        # return [file for file in self if isinstance(file, (File, Video, Img, Exe, Log))]
        return [f for f in self if not os.path.isdir(f.path)]

    @property
    def content(self) -> List[str]:
        return os.listdir(self.path)

    @property
    def directories(self) -> List[str]:
        """
        Return a list of subdirectory paths in the directory represented by this object.

        Returns:
        ----------
            list: A list of subdirectory paths
        """
        raise NotImplementedError("Depreciated method!")

    @property
    def rel_directories(self) -> List[str]:
        """
        Return a list of subdirectory paths relative to the directory represented by this object

        Returns:
            list: A list of subdirectory paths relative to the directory represented by this object
        """
        return [f".{folder.replace(self.path, "")}" for folder in self.directories]

    def objects(self) -> List[File]:
        """
        Convert each file in self to an appropriate type of object inheriting from File.

        Returns:
        ------
            The appropriate inhearitance of FileObject
        """
        if self._objects is None:
            self._objects = [file for file in self]
        return self._objects

    def file_info(self, file_name: str) -> File | None:
        """
        Query the object for files with the given name. Returns an appropriate FileObject if found.

        Paramaters
        ----------
            file_name (str): The name of the file

        Returns:
        ---------
            File (class) | None: Information about the specified file if found
        """
        if file_name not in self.files:
            return
        try:
            try:
                if file_name in os.listdir(self.path):
                    return obj(os.path.join(self.path, file_name))
            except (NotADirectoryError, FileNotFoundError):
                pass
            for d in self.directories:
                if file_name in os.listdir(os.path.join(self.path, d)):
                    return obj(os.path.join(self.path, d, file_name))
        except (FileNotFoundError, NotADirectoryError) as e:
            print(e)

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
        """Return a list of VideoObject instances found in the directory.

        Returns:
        --------
            List[VideoObject]: A list of VideoObject instances
        """
        return [item for item in self if isinstance(item, Video)]

    @property
    def dirs(self) -> List[File]:
        """Return a list of DirectoryObject instances found in the directory.

        Returns:
        ----------
            List[DirectoryObject]: A list of DirectoryObject instances
        """
        return [item for item in self if isinstance(item, Dir)]

    def sort(self) -> None:
        files = []
        for item in self:
            if item.is_file:
                file_stats = os.stat(item.path)
                atime = datetime.datetime.fromtimestamp(file_stats.st_atime).strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
                files.append((item.path, atime))

        files.sort(key=lambda x: x[1])
        files.reverse()
        # Print the table
        print(("{:<20}{:<40}").format("atime", "File"))
        for filepath, atime in files:
            print(("{:<20}{:<40}").format(atime, filepath.replace(self.path, "")))

    def __contains__(self, item: File) -> bool:
        """Compare items in two DirecoryObjects

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

    def __iter__(self) -> Iterator[File]:
        """
        Yield a sequence of File instances for each item in self

        Yields:
        -------
            any (File): The appropriate instance of File
        """
        # for file_path in chain(
        #     os.walk(self.path),
        #     [f"{directory}" for directory, _, _ in os.walk(self.path)],
        # ):
        #     yield obj(str(file_path))
        for root, _, files in os.walk(self.path):
            for file in files:
                path = os.path.join(root, file)  # full path of the file
                if os.path.isdir(path):
                    yield Dir(path)
                else:
                    yield obj(path)
            for directory in _:
                yield Dir(os.path.join(root, directory))

    def __eq__(self, other: File) -> bool:
        """Compare the contents of Dirs

        Parameters:
        ----------
            other (class): The class instance to compare with.

        Returns:
        ----------
            bool: True if the path of the two instances are equal, False otherwise.
        """
        if not isinstance(other, Dir):
            return False
        return self.content == other.content


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

    others = {re.compile(r"(\d+mhz|\d\.\d+v)"): Log}

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
