"""Represents a directory. Contains methods to list objects inside this directory."""

import datetime
import os
import re
from collections import defaultdict
from collections.abc import Iterator

from size import Converter
from ThreadPoolHelper import Pool

# from fsutils import File, Log, Exe, Video, Img
from .GenericFile import File
from .GitObject import Git
from .ImageFile import Img
from .LogFile import Log
from .ScriptFile import Exe
from .VideoFile import Video


class Dir(File):
    """
    A class representing information about a directory.

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
        - `files`       : Read only propery returning a list of file names
        - `objects`     : Read-only property yielding a sequence of DirectoryObject or FileObject instances
        - `directories` : Read-only property yielding a list of absolute paths for subdirectories

    """

    _objects: list[File] = []
    _directories: list["Dir"] = []
    _files: list[str] = []
    _metadata: dict = {}

    def __init__(self, path: str):
        super().__init__(path)

    @property
    def files(self) -> list[str]:
        """Return a list of file names in the directory represented by this object."""
        return [f.basename for f in self if not os.path.isdir(f.path)]

    @property
    def file_objects(self) -> list[File | Exe | Log | Img | Video | Git]:
        """Return a list of objects contained in the directory.

        This property iterates over all items in the directory and filters out those that are instances
        of File, Exe, Log, Img, Video, or Git, excluding directories.

        Returns:
        -------
            List[Union[File, Exe, Log, Img, Video, Git]]: A list of file objects.
        """
        return [
            item
            for item in self
            if isinstance(item, File | Exe | Log | Img | Video | Git)
            and not os.path.isdir(item.path)
        ]

    @property
    def content(self) -> list[str]:
        """List the the contents of the toplevel directory."""
        try:
            return os.listdir(self.path)
        except NotADirectoryError:
            return []

    @property
    def rel_directories(self) -> list[str]:
        """Return a list of subdirectory paths relative to the directory represented by this object"""
        return [f".{folder.path.replace(self.path, "")}" for folder in self.dirs]

    @property
    def objects(self) -> list[File | Exe | Log | Img | Video | Git]:
        """Return a list of fsutil objects inside self"""
        if not self._objects:
            self._objects = list(self.__iter__())
        return self._objects

    def file_info(self, file_name: str) -> File | None:
        """Query the object for files with the given name.

        Return an instance of the appropriate sub0class of File if a matching file is found."""
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

    @staticmethod
    def compare(dir1: "Dir", dir2: "Dir"):
        def process_item(item: File):
            return hash(item)

        def process_dir(file: "File"):
            if hash(file) in hash_set:
                return file.path, dir1.file_info(file.basename).path

        # Create a dictionary to store the hashes of files in dir1
        hash_set = set()
        identical_files = []
        # Execute the threaded operation and
        # calculate hashes for all files in dir1 and store them in hash_dict
        pool = Pool()
        for result in pool.execute(process_item, dir1.file_objects):
            hash_set.add(result)

        # Compare hashes of files in dir2 with those in hash_dict
        for result in pool.execute(process_dir, dir2.file_objects):
            identical_files.append(result)
            # for other_file in dir2.file_objects:
            # if hash(other_file) in hash_set:

        return identical_files

    @property
    def is_dir(self) -> bool:
        """Is the object a directory?"""
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
    def images(self) -> list[Img]:
        """Return a list of ImageObject instances found in the directory.

        Returns:
        --------
            List[ImageObject]: A list of ImageObject instances
        """
        return [item for item in self if isinstance(item, Img)]

    @property
    def videos(self) -> list[Video]:
        """Return a list of VideoObject instances found in the directory."""
        return [item for item in self if isinstance(item, Video)]

    @property
    def dirs(self) -> list[File]:
        """Return a list of DirectoryObject instances found in the directory."""
        return [item for item in self if isinstance(item, Dir)]

    @property
    def stat(self) -> None:
        """Print a formatted table of each file extention and their count."""
        if not self._metadata:
            self._metadata = defaultdict(int)
            for item in self.file_objects:
                ext = item.extension or ""
                self._metadata[ext[1:]] += 1  # Remove the dot from extention
        sorted_stat = dict(sorted(self._metadata.items(), key=lambda x: x[1]))
        # Print the sorted table
        max_key_length = max([len(k) for k in sorted_stat.keys()])
        for key, value in sorted_stat.items():
            print(f"{key: <{max_key_length}} {value}")

    @staticmethod
    def detect_duplicates():
        """Detect duplicate files in a directory and its subdirectories"""
        pass

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
        """Compare items in two DirectoryObjects"""
        if isinstance(item, File | Video | Img | Exe | Dir):
            return item in self.file_objects or item in self.dirs
            # return item.basename in self.files
        return item in self.files

    def __hash__(self) -> int:
        return hash((self.content, self.stat, self.is_empty))

    def __len__(self) -> int:
        """Return the number of items in the object"""
        return len(self.objects)

    def __iter__(self) -> Iterator[File | Exe | Log | Img | Video | Git]:
        """Yield a sequence of File instances for each item in self"""
        for root, _, files in os.walk(self.path):
            # Yield directories first to avoid unnecessary checks inside the loop
            for directory in _:
                yield Dir(os.path.join(root, directory))

            for file in files:
                path = os.path.join(root, file)  # full path of the file
                yield obj(path)

    def __eq__(self, other: "Dir", /) -> bool:
        """Compare the contents of two Dir objects"""
        return all(
            (
                isinstance(other, self.__class__),
                self.exists,
                other.exists,
                hash(self) == hash(other),
            )
        )

    # def fmt(self, *args) -> str:
    #     """Print a formatted string representation of each object in self."""
    #     return f"{self.__class__.__name__}({self.path})"

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(dir_name={self.path}, path={self.path}, is_empty={self.is_empty})".format(
            **vars(self)
        )


def obj(path: str) -> File:
    """Returns the appropriate subclass if File"""
    if not os.path.exists(path):
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
    }
    others = {
        re.compile(r"(\d+mhz|\d\.\d+v)"): Log,
        re.compile(r"([a-f0-9]{37,41})"): Git,
    }

    cls = classes.get(ext)
    if not cls:
        for k, v in others.items():
            if k.match(path.split(os.sep)[-1]):
                return v(path)
        if os.path.isdir(path):
            return Dir(path)
        return File(path)
    return cls(path)


if __name__ == "__main__":
    path = Dir("/home/joona/.dotfiles")
    from ExecutionTimer import ExecutionTimer

    with ExecutionTimer():
        for item in path.videos:
            if item.is_dir:
                print(item)
                print(item)
