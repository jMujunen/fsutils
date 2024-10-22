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

from size import Size
from ThreadPoolHelper import Pool

from fsutils.GenericFile import File
from fsutils.GitObject import Git
from fsutils.ImageFile import Img
from fsutils.LogFile import Log
from fsutils.mimecfg import FILE_TYPES
from fsutils.VideoFile import Video


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

    _objects: list[File]
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
    def file_objects(self) -> list[File | Log | Img | Video | Git]:
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
    def rel_directories(self) -> list[str]:
        """Return a list of subdirectory paths relative to the directory represented by this object."""
        return [f".{str(folder.path).replace(str(self.parent), "")}" for folder in self.dirs]

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
    def size(self) -> Size:
        """Return the total size of all files and directories in the current directory."""
        if hasattr(self, "_size") and self._size is not None:
            return self._size
        self._size = Size(
            sum(
                Pool().execute(
                    lambda x: x.size,
                    self.file_objects,
                    progress_bar=False,
                ),
            ),
        )
        return self._size

    @property
    def size_human(self) -> str:
        return str(self.size)

    def search(self, pattern: str, attr: str = "name") -> list[File]:
        """Query the object for files with the given `name | regex` pattern.

        Paramaters:
        -----------
            - pattern (str): The regular expression to search for.
            - attr (str): The attribute of the `File` object to search on.

        Return an list of `File` instances if found
        """
        return [obj for obj in self.file_objects if re.search(pattern, getattr(obj, attr))]

    def query_image(self, image: Img, threshold=10, method="phash") -> list[Img]:
        """Scan self for images with has values similar to the one of the given image."""
        pool = Pool()
        similar_images = []

        hash_to_query = image.calculate_hash(method)
        count = 0
        for result in pool.execute(lambda x: (x.calculate_hash, x), self.images, progress_bar=True):
            if result:
                h, img = result
                try:
                    distance = abs(hash_to_query - h)
                    print(f"{count:60}", end="\r")
                    if distance < threshold:
                        similar_images.append((img, distance))
                        count += 1
                except Exception:
                    print("\033[31mError while calculating hash difference: {e!r}\033[0m")
        return similar_images

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

    def sort(self, specifier: str, reverse=True) -> list[str]:
        """Sort the files and directories by the specifying attribute."""
        specs = {
            "mtime": lambda x: datetime.datetime.fromtimestamp(x.stat().st_mtime).strftime(
                "%Y-%m-%d %H:%M:%S",
            ),
            "ctime": lambda x: datetime.datetime.fromtimestamp(x.stat().st_ctime).strftime(
                "%Y-%m-%d %H:%M:%S",
            ),
            "atime": lambda x: datetime.datetime.fromtimestamp(x.stat().st_atime).strftime(
                "%Y-%m-%d %H:%M:%S",
            ),
            "size": lambda x: x.size,
            "name": lambda x: x.basename,
            "ext": lambda x: x.suffix,
        }
        result = sorted(
            [specs.get(specifier, "mtime")(file) for file in self.file_objects],
            key=lambda x: x[0],
            reverse=reverse,
        )

        # # Print the table
        format_string = "{:<25}{:<40}"
        print(format_string.format(specifier, "File"))
        for f in result:
            print(format_string.format(*f))
        return result

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
        match format_spec:
            case "videos":
                print(Video.fmtheader())
                return "\n".join(
                    result for result in pool.execute(format, self.videos, progress_bar=False)
                )
            case "images":
                print(Img.fmtheader())
                return "\n".join(
                    result for result in pool.execute(format, self.images, progress_bar=False)
                )
            case _:
                return f"Spec {format_spec} is not supported yet"

    def __contains__(self, item: File) -> bool:
        """Is `File` in self?"""  # noqa
        return item.sha256() in self.serialize()

    def __hash__(self) -> int:
        return hash((tuple(self.content), self.is_empty, tuple(self.rel_directories)))

    def __len__(self) -> int:
        """Return the number of items in the object."""
        return len(self.objects)

    def __iter__(self) -> Iterator[File]:
        """Yield a sequence of File instances for each item in self."""
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


def obj(path: str) -> File | None:
    """Return a File object for the given path."""
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
                return File(path)
    try:
        FileClass = File(path)
    except FileNotFoundError as e:
        return None
    return File(path)
