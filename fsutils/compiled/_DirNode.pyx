"""Represents a directory. Contains methods to list objects inside this directory."""
import cython
import datetime
import os
import pickle
import re
import sys
from collections import defaultdict
from collections.abc import Generator, Iterator
from pathlib import Path
from typing import LiteralString

from ThreadPoolHelper import Pool

from fsutils.GitObject import Git
from fsutils.ImageFile import Img
from fsutils.LogFile import Log, Presets
from fsutils.mimecfg import FILE_TYPES
from fsutils.VideoFile import Video
from fsutils.GitObject import Git
from fsutils.tools  import format_bytes
from fsutils.GenericFile import File


class Dir(File):
    """A class representing information about a directory.

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
    db: dict[str,list[str]] = {}
    def __init__(self, path: str | Path| None=None, *args, **kwargs) -> None:
        """Initialize a new instance of the Dir class.

        Parameters
        ----------
            path (str) : The path to the directory.

        """
        if not path:
            path = './'
        super().__init__(path, *args, **kwargs)
        self._pkl_path = Path(self.path, f".{self.prefix.removeprefix('.')}.pkl")
        depreciated_pkl = Path(self.path, f"{self.name.removeprefix('.')}.pkl")
        if depreciated_pkl.exists():
            depreciated_pkl.rename(self._pkl_path)
            print(f"Renamed \033[33m{depreciated_pkl.name}\033[0m -> {self._pkl_path.name}")

        if self._pkl_path.exists():
            self.db = pickle.loads(self._pkl_path.read_bytes())

        self.metadata = defaultdict(int)

    @property
    def files(self) -> list[str]:
        """Return a list of file names in the directory represented by this object."""
        return _cfiles(self)
    @property
    def file_objects(
        self,
    ) -> list[File | Log | Img | Video | Git]:
        """Return a list of objects contained in the directory.

        This property iterates over all items in the directory and filters out those that are instances
        of File,  Log, Img, Video, or Git, excluding directories.

        Returns
        -------
            List[File,  Log, Img, Video, Git]: A list of file objects.

        """
        return list(filter(lambda x: not isinstance(x, Dir), self))

    @property
    def content(self) -> list[str]:
        """List the the contents of the toplevel directory."""
        try:
            return os.listdir(self.path)
        except NotADirectoryError:
            return []

    @property
    def objects(self) -> list[File]:
        """Return a list of fsutils objects inside self."""
        try:
            self._objects = list(self.__iter__())
        except AttributeError:
            self._objects = []
        return self._objects

    @property
    def is_empty(self) -> bool:
        """Check if the directory is empty."""
        return len(self.files) == 0

    @property
    def images(self) -> list[Img]:
        """A list of ImageObject instances found in the directory."""
        return list(filter(lambda x: isinstance(x, Img), self.__iter__()))  # type: ignore

    @property
    def videos(self) -> list[Video]:
        """A list of VideoObject instances found in the directory."""
        return list(filter(lambda x: isinstance(x, Video), self.__iter__()))  # type: ignore

    @property
    def logs(self) -> list[Log]:
        """A list of Log instances found in the directory."""
        return list(filter(lambda x: isinstance(x, Log), self.__iter__()))  # type: ignore

    @property
    def dirs(self) -> list[File]:
        """A list of DirectoryObject instances found in the directory."""
        return list(filter(lambda x: isinstance(x, Dir), self.__iter__()))

    @property
    def describe(self) -> None:
        """Print a formatted table of each file extention and their count."""
        if not self.metadata:
            self.metadata = defaultdict(int)
            for item in self.file_objects:
                ext = item.suffix or ""
                if ext == "":
                    self.metadata["None"] += 1
                    continue
                self.metadata[ext[1:]] += 1  # Remove the dot from extention
        sorted_stat = dict(sorted(self.metadata.items(), key=lambda x: x[1]))
        # Print the sorted table
        if not sorted_stat:
            print("No files found.")
            return None
        max_key_length = max([len(k) for k in sorted_stat])
        total = sum([v for k, v in sorted_stat.items()])
        total_digits = len([int(i) for i in list(str(total))])
        for key, value in sorted_stat.items():
            percentage = round((int(value) / total) * 100, 1)
            if percentage < 5:
                color = ""
            elif 5 < percentage < 20:
                color = ""
            elif 20 <= percentage < 50:
                color = ""
            else:
                color = ""
            print(
                f"{key: <{max_key_length+1}} {value:<{total_digits+4}} {color}{percentage}"
            )
        print(
            f"{'Total': <{max_key_length+1}} {total:<{total_digits+5}}{'100%':}",
            end="\n",
        )

    @property
    def size(self) -> int:
        """Return the total size of all files and directories in the current directory."""
        if hasattr(self, "_size") and self._size is not None:
            return self._size
        pool = Pool()
        self._size = sum(
                pool.execute(
                    lambda x: x.size,
                    self.file_objects,
                    progress_bar=False,
                ),
            )
        return self._size

    @property
    def size_human(self) -> str:
        return format_bytes(self.size)


    def duplicates(self, num_keep=2, refresh: bool = False) -> list[list[str]]:
        """Return a list of duplicate files in the directory.

        Uses pre-calculated hash values to find duplicates.

        Paramaters:
        -----------
            - num_keep (int): The number of copies of each file to keep.
            - refresh (bool): If True, re-calculate the hash values for all files
        """
        hashes = self.serialize(replace=refresh)
        return [value for value in hashes.values() if len(value) > num_keep]

    def load_database(self) -> dict[int, list[str]]:
        """Deserialize the pickled database."""
        if self._pkl_path.exists():
            return pickle.loads(self._pkl_path.read_bytes())
        return {}

    def serialize(self, replace=False) -> dict[int, list[str]]:
        """Create an hash index of all files in self."""
        if self._pkl_path.exists() and replace is True:
            self._pkl_path.unlink()
            self.db = {}
        elif self._pkl_path.exists() and replace is False:
            return self.load_database()
        return serialize(self, int(replace))

    def sha256(self) -> str:
        return super().sha256()

    def __format__(self, format_spec: str, /) -> LiteralString | str:
        pool = Pool()
        if format_spec == "videos":
            print(Video.fmtheader())
            return "\n".join(
                result for result in pool.execute(format, self.videos, progress_bar=False)
            )
        elif format_spec == "images":
            print(Img.fmtheader())
            return "\n".join(
                result for result in pool.execute(format, self.images, progress_bar=False)
            )
        else:
            raise ValueError("Invalid format specifier")

    def __contains__(self, item: File) -> bool:
        """Is `File` in self?"""  # noqa
        return bool(_c_contains(self, item))

    def __hash__(self) -> int:
        return hash((tuple(self.content), self.is_empty))

    def __len__(self) -> int:
        """Return the number of items in the object."""
        return len(list(self.rglob("*")))

    def __iter__(self): # -> Iterator[File]:
        """Yield a sequence of File instances for each item in self."""
        cdef int num_objects = len(self._objects)
        cdef int NULL_INT = 0
        if num_objects == NULL_INT:
            yield from walk(self)
        else:
            yield from self._objects

    def __eq__(self, other: "Dir", /) -> bool:
        """Compare the contents of two Dir objects."""
        return all(
            (
                isinstance(other, self.__class__),
                hash(self) == hash(other),
            ),
        )

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name}, size={self.size_human}, is_empty={self.is_empty})".format(
            **vars(self),
        )


cdef _obj(str path):
    """Return a File object for the given path."""
    cdef unicode ext, file_type
    cdef str class_name


    pathobj = Path(path)
    if pathobj.is_dir():
        return Dir(path)
    ext = pathobj.suffix.lower()

    for file_type, extensions in FILE_TYPES.items():
        if ext in extensions:
            # Dynamically create the class name and instantiate it
            class_name = file_type.capitalize()
            module = sys.modules[__name__]
            try:
                FileClass = getattr(module, class_name)
                return FileClass(path)
            except FileNotFoundError as e:
                print(f"{e!r}")
            except AttributeError:
                class_name = 'File'
                return File(path)
    try:
        FileClass = File(path)
    except FileNotFoundError as e:
        return None
    return File(path)


cdef serialize(dirObj,  int replace=0):
    """Create an hash index of all files in dirObj."""
    cdef tuple result
    cdef unicode sha, path


    if dirObj._pkl_path.exists() and replace == 1:
        dirObj._pkl_path.unlink()
        dirObj.db = {}
    elif dirObj._pkl_path.exists() and replace  == 0:
        return dirObj.load_database()

    pool = Pool()

    for result in pool.execute(
        lambda x: (x.sha256(), x.path),
        dirObj.file_objects,
        progress_bar=True,
    ):
        if result:
            sha, path = result
            if sha not in dirObj.db:
                dirObj.db[sha] = [path]
            else:
                dirObj.db[sha].append(path)
    dirObj._pkl_path.write_bytes(pickle.dumps(dirObj.db))
    return dirObj.db

cdef list walk(self):
    """Yield a sequence of File instances for each item in self."""
    cdef int num_objects = len(self._objects)
    cdef int null_int = 0
    cdef unicode root, directory
    cdef list _, files


    if num_objects == null_int:
        for root, _, files in os.walk(self.path):
            # Yield directories first to avoid unnecessary checks inside the loop
            for directory in _:
                obj = Dir(os.path.join(root, directory))  # noqa
                self._objects.append(obj)
                continue
            for file in files:
                obj = _obj(os.path.join(root, file))  # noqa
                if obj is not None:
                    self._objects.append(obj)
    return self._objects
cdef list[str] _cfiles(self):
    cdef list[str] files = []
    for f in self.objects:
        try:
            if not f.is_dir():
                files.append(f.name)
        except Exception as e:
            # continue
            print(f"{e}: {f}")
    return files


cdef bint _c_contains(self, item):
    cdef dict db = self.serialize()
    cdef unicode sha256 = item.sha256()
    return int(item in db)

def obj(file_path: str):
    """Return a File instance for the given file path."""
    return _obj(file_path)