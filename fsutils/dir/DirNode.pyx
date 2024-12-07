"""Represents a directory. Contains methods to list objects inside this directory."""
import os
import pickle
import sys
from collections import defaultdict
import subprocess
from collections.abc import Generator, Iterator
from pathlib import Path
from typing import LiteralString, Optional, Iterator, Generator
import glob


from  typing import Generator
import os
from pathlib import Path
import glob
from cython.parallel import prange

from ThreadPoolHelper import Pool

from fsutils.git import Git
from fsutils.img import Img
from fsutils.log import Log
from fsutils.utils import FILE_TYPES, IGNORED_DIRS
from fsutils.video import Video
from fsutils.tools  import format_bytes
from fsutils.file import File


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
        - `files`       : Read only property returning a list of file names
        - `objects`     : Read-only property yielding a sequence of DirectoryObject or FileObject instances
        - `directories` : Read-only property yielding a list of absolute paths for subdirectories

    """
    _objects: list[File]
    # _files: list[os.DirEntry|Path]
    # _dirs: list[Path]

    def __init__(self, path: Optional[str | Path] = None, *args, **kwargs) -> None:
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

        self._db = pickle.loads(self._pkl_path.read_bytes()) if self._pkl_path.exists() else {}
        self._objects = []
        # Remove a few unnecessary attributes from inherited class
        del self.encoding
    @property
    def file_objects(
        self,
    ) -> list[File | Log | Img | Video | Git]:
        """Return a list of objects contained in the directory.

        This property iterates over all items in the directory
        and filters out those that are instances of File,  Log,
        Img, Video, or Git, excluding directories.

        Returns
        -------
            List[File,  Log, Img, Video, Git]: A list of file objects.

        """
        return list(filter(lambda x: not isinstance(x, Dir), self.__iter__()))

    @property
    def content(self) -> list[str]:
        """List the the contents of the toplevel directory."""
        try:
            return os.listdir(self.path)
        except NotADirectoryError:
            return []


    def objects(self) -> Generator:
        """Return a list of fsutils objects inside self."""
        try:
            yield from self.__iter__()
        except AttributeError:
            yield from self._objects


    def is_empty(self) -> bool:
        """Check if the directory is empty."""
        try:
            if next(iter(self.ls_files())):
                return False
        except StopIteration:
            return True
        return False

    def images_(self) -> list[Img]:
        """A list of ImageObject instances found in the directory."""
        return list(filter(lambda x: isinstance(x, Img), self.__iter__()))  # type: ignore

    def videos_(self) -> list[Video]:
        """A list of VideoObject instances found in the directory."""
        return list(filter(lambda x: isinstance(x, Video), self.__iter__()))  # type: ignore

    def logs(self) -> list[Log]:
        """A list of Log instances found in the directory."""
        return list(filter(lambda x: isinstance(x, Log), self.__iter__()))  # type: ignore

    def describe(self, bint include_size=False) -> dict[str, int]:  # type: ignore
        """Print a formatted table of each file extention and their count."""
        cdef str key
        cdef list[str] ext
        cdef unsigned int max_key_length, value
        cdef unsigned long int total, num_total
        cdef float percentage

        # cdef dictsorted_stat, file_types
        file_types = defaultdict(int)
        for item in self.ls_files():
            ext = item.path.split(os.sep)[-1].split(".")
            if len(ext) > 1:
                file_types[ext[-1]] += 1
            else:
                file_types["other"] += 1

        sorted_stat = dict(sorted(file_types.items(), key=lambda x: x[1]))
        # Print the sorted table
        if not sorted_stat:
            return {}

        max_key_length = max([len(k) for k in sorted_stat]) + 1
        total = sum([v for v in sorted_stat.values()])
        num_total = len([int(i) for i in list(str(total))]) + 5
        color = ''
        # bar_width = 100  # Width of the bar chart
        for key, value in filter(lambda x: file_types[x[0]] / total > 0.01, sorted_stat.items()):
            percentage = (int(value) / total) * 100
            if percentage < 1:
                continue
            elif percentage < 5:
                color = "\033[37m"
            elif 5 < percentage < 20:
                color = ""
            elif 20 <= percentage < 50:
                color = "\033[32m"
            else:
                color = "\033[31m"
            bars = f'█' *  int((value / total) * 50)
            print(f"{key: <{8}} {bars:<50} {value:<{num_total-1}} {color}{percentage:.2f}%\033[0m")
            # print(
            #     f"{key: <{max_key_length}} {value:<{num_total-1}} {color}{percentage:.2f}\033[0m"
            # )
        return sorted_stat


    @property
    def db(self):
        if not self._db:
            self._db = self.load_database(replace=True) # type: ignore
        else:
            return self._db
    @property
    def size(self) -> int:
        """Return the total size of all files and directories in the current directory."""
        if hasattr(self, "_size"):
            if self._size is not None:
                return self._size
        awk = "awk '{ print $1 }'"
        cmd = f'du -bsx "{self.path}" | {awk}'
        self._size = int(subprocess.getoutput(cmd))
        return self._size

    @property
    def size_human(self) -> str:
        return format_bytes(self.size)


    def duplicates(self, int num_keep=2, updatedb=False) -> list[list[str]]:
        """Return a list of duplicate files in the directory.

        Uses pre-calculated hash values to find duplicates.

        Paramaters:
        -----------
            - num_keep (int): The number of copies of each file to keep.
            - updatedb (bool): If True, re-calculate the hash values for all files
        """
        cdef dict[str, list[str]] hashes
        hashes = self.serialize(replace=updatedb) # type: ignore
        return [value for value in hashes.values() if len(value) > num_keep] # type: ignore

    def load_database(self) -> dict[str, list[str]]:
        """Deserialize the pickled database."""
        if self._pkl_path.exists():
            return pickle.loads(self._pkl_path.read_bytes())
        return {}

    def serialize(self, bint replace=True, bint progress_bar=True) ->  dict[str, list[str]]:# type: ignore
        """Create an hash index of all files in self."""
        cdef tuple result
        cdef str sha, path

        self._pkl_path = Path(self._pkl_path.parent, f".{self._pkl_path.name.lstrip('.')}")
        if self._pkl_path.exists() and replace:
            self._pkl_path.unlink()
            self._db = {}
        elif self._pkl_path.exists() and replace is False:
            return self.load_database()

        pool = Pool()

        for result in pool.execute(
            worker,
            self.file_objects,
            progress_bar=progress_bar,
        ):
            if result:
                sha, path = result
                if sha not in self._db:
                    self._db[sha] = [path]
                else:
                    self._db[sha].append(path)
        self._pkl_path.write_bytes(pickle.dumps(self._db))
        return self._db
    def compare(self, other: 'Dir') -> tuple[set[str], set[str]]:
        """Compare the current directory with another directory."""
        cdef set[str] common_files, unique_files
        cdef unsigned int num_files = len(set(self.ls_files()))
        cdef str template = '{key:<10} {color}{value:<10}{reset}{percentage}'

        common_files = set(self._db.keys()) & set(other._db.keys())
        unique_files = set(self._db.keys()) - set(other._db.keys())

        print(template.format(key='Total: ',color='\033[35m', reset='\033[0m', value=num_files, percentage=""))
        print(template.format(key="Common: ", color='\033[34m', reset='\033[0m',value=len(common_files),percentage=f"{len(common_files)/num_files*100:.0f}%"))
        print(template.format(key="Unique: ", color='\033[32m', reset='\033[0m',value=len(unique_files),percentage=f"{len(unique_files)/num_files*100:.0f}%"))

        return common_files, unique_files




    def ls(self, follow_symlinks=False, recursive=True) -> Generator[os.DirEntry, None, None]:
        if not recursive:
            yield from os.scandir(self.path)
        yield from self.traverse(follow_symlinks=follow_symlinks)

    def ls_dirs(self,follow_symlinks=False) -> Generator[os.DirEntry, None, None]:
        """Return a list of paths for all directories in self."""
        for item in self.ls():
            if item.is_dir(follow_symlinks=follow_symlinks):
                yield item
    def ls_files(self,follow_symlinks=False) -> Generator[os.DirEntry, None, None]:
        """Return a list of paths for all files in self."""
        for item in self.ls():
            if item.is_file(follow_symlinks=follow_symlinks):
                yield item

    def traverse(self, root=None, follow_symlinks=False) -> Generator[os.DirEntry, None, None]:
        """Recursively traverse a directory tree starting from the given path.

        Yields
        ------
            Generator[os.DirEntry]
        """
        cdef str path = self.path if root is None else root
        with os.scandir(path) as entries:
            for entry in entries:
                try:
                    if entry.is_file(follow_symlinks=follow_symlinks):
                        yield entry
                    elif entry.is_dir(follow_symlinks=follow_symlinks):
                        yield from self.traverse(root=entry.path, follow_symlinks=follow_symlinks)
                        yield entry
                except PermissionError:
                    continue

    def videos(self) -> Generator[Video, None, None]:
        """Return a generator of Video objects for all video files."""
        for file in self.ls_files():
            if file.name.endswith((".mp4", ".avi", ".mkv")):
                yield Video(file.path)

    def images(self) -> Generator[Img, None, None]:
        """Return a generator of Img objects for all image files."""
        for file in self.ls_files():
            if file.name.endswith((".jpg", ".jpeg", ".png", ".gif")):
                yield Img(file.path)


    def __getitem__(self, key: str) -> File:
        """Get a file by name."""
        for item in self.ls():
            if item.name == key:
                yield _obj(item.path)
        raise KeyError(f"File '{key}' not found")


    def __format__(self, format_spec: str, /) -> LiteralString | str:
        pool = Pool()
        if format_spec == "videos":
            print(Video.fmtheader())
            return "\n".join(
                result for result in pool.execute(format, self.videos(), progress_bar=False)
            )
        elif format_spec == "images":
            print(Img.fmtheader())
            return "\n".join(
                result for result in pool.execute(format, self.images(), progress_bar=False)
            )
        else:
            raise ValueError("Invalid format specifier")

    def __contains__(self, other: File) -> bool:
        """Is `File` in self?"""  # noqa
        self._db = self.serialize(replace=True, progress_bar=False) # type: ignore
        return hash(other) in self._db

    def __hash__(self) -> int:
        return hash((tuple(self.content), self.is_empty))

    def __len__(self) -> int:
        """Return the number of items in the object."""
        return len(list(self.traverse()))

    def __iter__(self) -> Iterator[File]:
        """Yield a sequence of File instances for each item in self."""
        cdef unicode root, directory
        cdef list[str] _, files
        if self._objects:
            yield from self._objects
        else:
            for root, _, files in os.walk(self.path):
                # Yield directories first to avoid unnecessary checks inside the loop
                for directory in _:
                    cls_instance = Dir(os.path.join(root, directory))
                    yield cls_instance
                    self._objects.append(cls_instance)
                for file in files:
                    cls_instance = _obj(os.path.join(root, file))
                    yield cls_instance
                    self._objects.append(cls_instance)

    def __eq__(self, other: "Dir", /) -> bool:
        """Compare the contents of two Dir objects."""
        return all(
            (
                isinstance(other, self.__class__),
                hash(self) == hash(other),
            ),
        )

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name}, size={self.size_human}, is_empty={self.is_empty()})".format(
            **vars(self),
        )


cdef _obj(str path):
    """Return a File object for the given path."""
    cdef unicode ext, file_type
    cdef list[str] extensions
    cdef str class_name
    cdef object FileClass

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
                return FileClass(path) # type: ignore
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


def obj(file_path: str):
    """Return a File instance for the given file path."""
    return _obj(file_path)

cdef tuple[str, str] worker(item):
    """Worker function to process items in parallel."""
    return item.sha256(), item.path

