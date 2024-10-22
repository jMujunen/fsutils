"""Represents a directory. Contains methods to list objects inside this directory."""

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

from . import GenericFile
from . import GitObject
from . import ImageFile
from . import LogFile
from . import mimecfg
from . import VideoFile
from . import GitObject
from . import tools

class Dir(GenericFile.File):
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
        - `__iter__`  :             # Iterator which yields the appropriate GenericFile.File instance


    Properties
    -----------
        - `files`       : Read only propery returning a list of file names
        - `objects`     : Read-only property yielding a sequence of DirectoryObject or FileObject instances
        - `directories` : Read-only property yielding a list of absolute paths for subdirectories

    """

    _objects: list[GenericFile.File]
    encoding: None = None

    def __init__(self, path: str | Path, *args, **kwargs) -> None:
        """Initialize a new instance of the Dir class.

        Parameters
        ----------
            path (str) : The path to the directory.

        """
        super().__init__(path, *args, **kwargs)
        self._pkl_path = Path(self.path, f"{self.prefix}.pkl")
        if self._pkl_path.exists():
            self.db = pickle.loads(self._pkl_path.read_bytes())
        else:
            self.db = {}
        # MetaData.__post_init__(self)
        self._objects = []
        self.metadata = defaultdict(int)

    @property
    def files(self) -> list[str]:
        """Return a list of file names in the directory represented by this object."""
        files = []
        for f in self.objects:
            try:
                if not f.is_dir():
                    files.append(f.name)
            except Exception as e:
                # continue
                print(f"{e}: {f}")
        return files
        # return [f.name for f in self.objects if not f.is_dir()]

    @property
    def file_objects(
        self,
    ) -> list[GenericFile.File | LogFile.Log | ImageFile.Img | VideoFile.Video | GitObject.Git]:
        """Return a list of objects contained in the directory.

        This property iterates over all items in the directory and filters out those that are instances
        of GenericFile.File,  LogFile.Log, ImageFile.Img, VideoFile.Video, or Git, excluding directories.

        Returns
        -------
            List[GenericFile.File,  LogFile.Log, ImageFile.Img, VideoFile.Video, Git]: A list of file objects.

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
    def objects(self) -> list[GenericFile.File]:
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
    def images(self) -> list[ImageFile.Img]:
        """A list of ImageObject instances found in the directory."""
        return list(filter(lambda x: isinstance(x, ImageFile.Img), self.__iter__()))  # type: ignore

    @property
    def videos(self) -> list[VideoFile.Video]:
        """A list of VideoObject instances found in the directory."""
        return list(filter(lambda x: isinstance(x, VideoFile.Video), self.__iter__()))  # type: ignore

    @property
    def logs(self) -> list[LogFile.Log]:
        """A list of LogFile.Log instances found in the directory."""
        return list(filter(lambda x: isinstance(x, LogFile.Log), self.__iter__()))  # type: ignore

    @property
    def dirs(self) -> list[GenericFile.File]:
        """A list of DirectoryObject instances found in the directory."""
        return list(filter(lambda x: isinstance(x, Dir), self.__iter__()))

    @property
    def summary(self) -> None:
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
        max_key_length = max([len(k) for k in sorted_stat])
        for key, value in sorted_stat.items():
            print(f"{key: <{max_key_length}} {value}")

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
        return str(self.size)

    def search(self, pattern: str, attr: str = "name") -> list[GenericFile.File]:
        """Query the object for files with the given `name | regex` pattern.

        Paramaters:
        -----------
            - pattern (str): The regular expression to search for.
            - attr (str): The attribute of the `GenericFile.File` object to search on.

        Return an list of `GenericFile.File` instances if found
        """
        return [obj for obj in self.file_objects if re.search(pattern, getattr(obj, attr))]

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

    def serialize(self, *, replace=False) -> dict[int, list[str]]:
        """Create an hash index of all files in self."""
        if self._pkl_path.exists() and replace is True:
            self._pkl_path.unlink()
            self.db = {}
        elif self._pkl_path.exists() and replace is False:
            return self.load_database()

        pool = Pool()

        for result in pool.execute(
            lambda x: (x.sha256(), x.path),
            self.file_objects,
            progress_bar=True,
        ):
            if result:
                sha, path = result
                if sha not in self.db:
                    self.db[sha] = [path]
                else:
                    self.db[sha].append(path)
        self._pkl_path.write_bytes(pickle.dumps(self.db))
        return self.db

    def sha256(self) -> str:
        return super().sha256()

    def __format__(self, format_spec: str, /) -> LiteralString | str:
        pool = Pool()
        if format_spec == "videos":
            print(VideoFile.Video.fmtheader())
            return "\n".join(
                result for result in pool.execute(format, self.videos, progress_bar=False)
            )
        elif format_spec == "images":
            print(ImageFile.Img.fmtheader())
            return "\n".join(
                result for result in pool.execute(format, self.images, progress_bar=False)
            )
        else:
            raise ValueError("Invalid format specifier")

    def __contains__(self, item: GenericFile.File) -> bool:
        """Is `GenericFile.File` in self?"""  # noqa
        return item.sha256() in self.serialize()

    def __hash__(self) -> int:
        return hash((tuple(self.content), self.is_empty))

    def __len__(self) -> int:
        """Return the number of items in the object."""
        return len(self.objects)

    def __iter__(self) -> Iterator[GenericFile.File]:
        """Yield a sequence of GenericFile.File instances for each item in self."""
        if len(self._objects) == 0:
            for root, _, files in os.walk(self.path):
                # Yield directories first to avoid unnecessary checks inside the loop
                for directory in _:
                    _obj = Dir(os.path.join(root, directory))  # noqa
                    self._objects.append(_obj)

                for file in files:
                    _obj = obj(os.path.join(root, file))  # noqa
                    if _obj is not None:
                        self._objects.append(_obj)
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


def obj(path: str) -> GenericFile.File | None:
    """Return a GenericFile.File object for the given path."""
    pathobj = Path(path)
    if pathobj.is_dir():
        return Dir(path)
    ext = pathobj.suffix.lower()

    for file_type, extensions in mimecfg.FILE_TYPES.items():
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
                return GenericFile.File(path)
    try:
        FileClass = GenericFile.File(path)
    except FileNotFoundError as e:
        return None
    return GenericFile.File(path)


path = Dir("~/Pictures")
print(path)
