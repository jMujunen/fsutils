# cython: boundscheck=False, wraparound=False, divide_zero_check=False, cdivsion=True

"""Represents a directory. Contains methods to list objects inside this directory."""

import os
import pickle
import sys
from collections import defaultdict
import subprocess
from pathlib import Path
from typing import Iterator, Generator
import os
cimport cython
import fnmatch
from libc.stdlib cimport free
from libc.stdint cimport uint8_t

from ThreadPoolHelper import Pool
from fsutils.img import Img
from fsutils.utils.mimecfg import FILE_TYPES
from fsutils.video import Video
from fsutils.utils.tools  import format_bytes
from fsutils.file.GenericFile cimport Base


cdef class Dir(Base):
    """A class representing information about a directory.

    Attributes
    ----------
        - `path (str)` : The path to the directory.

    Methods
    -------
        - `describe()` :            # Returns a list of extentions and their count
        - `compare(other)` :        # Compare properties of two Dir objects
        - `duplicates(num_keep=2)`   # Returns a list of duplicate files in this directory
        - `filter(ext)` :           # Returns a list of files that match the given extension
        - `glob(pattern)` :         # Returns a list of files that match the given pattern
        - `is_empty()` :            # Returns True if the directory is empty, False otherwise
        - `load_database()` :       # Load indexed database
        - `ls()` :                  # List the contents of the toplevel directory
        - `ls_dirs()` :             # List the contents of the toplevel directory as directories
        - `traverse()` :             # Traverse the directory tree and yield all files
        - `serialize()` :           # Serialize the directory index
        - `non_media()` :           # Returns a list of non-media files in this directory
        - `videos()` :              # Returns a list of video objects in this directory
        - `images()` :              # Returns a list of image objects in this directory
        - `fileobjects()` :         # Returns a list of files objects in this directory

    Properties
    -----------
        - `files`       : Read only property returning a list of file names
        - `dirs` : Read-only property yielding a list of absolute paths for subdirectories
        - `content` : List the the contents of the toplevel directory
        - `size`  : Read-only property returning the size of the directory in bytes.
        - `size_human`  : Read-only property returning the size of the directory in human readable format.

    """
    def __cinit__(self, str path='./'):
        self.path = path
        self._pkl_path = str(Path(self.path, f".{self.prefix.removeprefix('.')}.pkl"))
        self._db = {}

    def __init__(self, path: str = './') -> None:
        """Initialize a new instance of the Dir class.

        Parameters
        ----------
            path (str) : The path to the directory.

        """
        super().__init__(path)
        self._pkl_path = str(Path(self.path, f".{self.prefix.removeprefix('.')}.pkl"))

    @property
    def dirs(self) -> list[str]:
        """Return a list of all directories in the directory."""
        return list(self.ls_dirs())
    @property
    def files(self) -> list[str]:
        """Return a list of all files in the directory."""
        return list(self.ls_files())

    @property
    def content(self) -> list[str]:
        """List the the contents of the toplevel directory."""
        try:
            return os.listdir(self.path)
        except NotADirectoryError:
            return []

    def is_empty(self) -> bool:
        """Check if the directory is empty."""
        try:
            if next(iter(self.ls_files())):
                return False
        except StopIteration:
            return True
        return False

    def videos(self) -> list[Video]:
        cdef tuple[str] valid_exts = FILE_TYPES['video']
        return [Video.__new__(Video, file) for file in self.ls_files() if file.lower().endswith(valid_exts)]

    def images(self) -> list[Img]:
        cdef tuple[str] valid_exts = FILE_TYPES['img']
        return [Img.__new__(Img, file) for file in self.ls_files() if file.lower().endswith(valid_exts)]

    def non_media(self) -> list[Base]:
        """Return a generator of all files that are not media."""
        cdef tuple[str] valid_exts = (*FILE_TYPES['video'],*FILE_TYPES['img'])
        return [Base.__new__(Base, file) for file in self.ls_files() if not file.lower().endswith(valid_exts)] # type: ignore

    def fileobjects(self) -> list[Base]:
        """Return a list of all file objects."""
        return [obj(file) for file in self.ls_files()] # type: ignore

    @cython.wraparound(False)
    @cython.boundscheck(False)
    def describe(self, bint print_result=True) -> dict[str, int]:
        """Print a formatted table of each file extention and their count."""
        cdef str key
        cdef str ext, _
        cdef unsigned int value
        cdef unsigned long int total, num_total
        cdef float percentage
        cdef str red, green, gray

        gray = "\033[37m"
        red = "\033[31m"
        green = "\033[32m"

        file_types = defaultdict(int)
        for item in self.ls_files():
            _, ext = os.path.splitext(item)
            if not ext:
                file_types["other"] += 1
                continue
            file_types[ext] += 1


        sorted_stat = dict(sorted(file_types.items(), key=stat_result))
        # Print the sorted table
        if not sorted_stat:
            return {}

        if print_result is True:
            total = sum([v for v in sorted_stat.values()])
            num_total = len([int(i) for i in list(str(total))]) + 5
            color = ''
            for key, value in sorted_stat.items():
                percentage = (int(value) / total) * 100
                if percentage < 1:
                    continue
                elif percentage < 5:
                    color = gray
                elif 5 < percentage < 20:
                    color = ""
                elif 20 <= percentage < 50:
                    color = green
                else:
                    color = red
                bars = f'█' *  int((value / total) * 50)
                print(f"{key: <{8}} {bars:<50} {value:<{num_total-1}} {color}{percentage:.2f}%\033[0m")
            print(
                f"{'total': <{8}} {' ':<50} {total:<{num_total-1}}"
            )
        return sorted_stat


    @property
    def db(self) -> dict[str, set[str]]:
        if not self._db:
            self._db = self._load_database()
        return self._db
    @db.setter
    def db(self, value: dict[str, set[str]]):# -> dict[str, set[str]]:
        self._db = value
    @property
    def size(self) -> int:
        """Size of all files and directories in the current directory."""
        if hasattr(self, "_size"):
            if self._size:
                return self._size
        awk = "awk '{ print $1 }'"
        cmd = f'du -bsx "{self.path}" | {awk}'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.stdout.strip():
            self._size = int(result.stdout.strip())
        else:
            self._size = 0
        return self._size

    @property
    def size_human(self) -> str:
        """Size of directory in human-readable format."""
        return format_bytes(self.size)

    def duplicates(self, unsigned short int num_keep=2, bint updatedb=False) -> list[list[str]]: # type: ignore
        """Return a list of duplicate files in the directory.

        Uses pre-calculated hash values to find duplicates.

        Paramaters:
        -----------
            - num_keep (int): The number of copies of each file to keep.
            - updatedb (bint): If True, re-calculate the hash values for all files
        """
        cdef dict[str, set[str]] hashes
        hashes = self.serialize(replace=updatedb) # type: ignore
        return [list(value) for value in hashes.values() if len(value) > num_keep]

    def _load_database(self) -> dict[str, set[str]]:
        """Deserialize the pickled database."""
        return pickle.loads(Path(self._pkl_path).read_bytes()) if Path(self._pkl_path).exists() else {}
    @cython.wraparound(False)
    @cython.boundscheck(False)
    def serialize(self, **kwargs) ->  dict[str, set[str]]:
        """Create an hash index of all files in self.

        Paramaters
        ----------
            - replace (bint): If True, re-calculate the hash values for all files

        Returns
        -------
            - dict[str, set[str]]: A dictionary where the keys are hash values
                and the values are lists of file paths.

        """
        if len(self.files) == 0:
            with open(self._pkl_path, 'wb') as f:
                pickle.dump({}, f)
            return {}
        cdef bytes _path = self.path.encode('utf-8')
        cdef char* path = <char*>_path
        cdef HashMap *_map
        cdef char* _filepath
        cdef uint8_t _sha[32]

        mapping = defaultdict(set)

        self._pkl_path = self._pkl_path.lstrip('.')
        if Path(self._pkl_path).exists():
            Path(self._pkl_path).unlink()
        elif Path(self._pkl_path).exists() and kwargs.get('replace', True) is False:
            return self.db

        with nogil:
            _map = hashDirectory(path)
        if _map is not NULL:
            for i in range(_map.size):
                _filepath = _map.entries[i].filepath
                _sha = _map.entries[i].sha._hash
                sha = ''.join([format(_sha[i], '02x') for i in range(0,32)])
                mapping[sha].add(_filepath.decode('utf-8'))
            free(_map.entries)
            free(_map)

        self.db = dict(mapping)
        serialized_object = pickle.dumps(self.db)
        with open(self._pkl_path, 'wb') as f:
            f.write(serialized_object)
        return self.db

    def compare(self, Dir other) -> tuple[set[str], set[str]]:
        """Compare the current directory with another directory."""
        cdef set[str] common_files, unique_files, self_db, other_db
        cdef unsigned int num_files = len(set(self.ls_files()))
        cdef str template = '{key:<10} {color}{value:<10}{reset}{percentage}'
        cdef str green, purple, blue, reset

        green = '\033[32m'
        blue = '\033[34m'
        reset = '\033[0m'
        purple = '\033[35m'

        self_db = set(self.db.keys())
        other_db = set(other.db.keys())

        common_files = self_db & other_db
        unique_files = self_db - other_db

        print(template.format(key='Total: ',color=purple, reset=reset, value=num_files, percentage=""))
        print(template.format(key="Common: ", color=blue, reset=reset,value=len(common_files),percentage=f"{len(common_files)/num_files*100:.0f}%"))
        print(template.format(key="Unique: ", color=green, reset=reset,value=len(unique_files),percentage=f"{len(unique_files)/num_files*100:.0f}%"))

        return common_files, unique_files

    def ls(self, bint follow_symlinks=False, bint recursive=True) -> Generator[os.DirEntry, None, None]: # type: ignore
        if not recursive:
            yield from os.scandir(self.path)
        yield from self.traverse(follow_symlinks=follow_symlinks)

    def ls_dirs(self,bint follow_symlinks=False) -> Generator[str, None, None]:
        """Return a list of paths for all directories in self."""
        for item in self.ls():
            if item.is_dir(follow_symlinks=follow_symlinks): # type: ignore
                yield item.path

    def ls_files(self,bint follow_symlinks=False) -> Generator[str, None, None]:
        """Return a list of paths for all files in self."""
        for item in self.ls():
            if item.is_file(follow_symlinks=follow_symlinks):
                yield item.path

    def traverse(self, root=None, bint follow_symlinks=False) -> Generator[os.DirEntry, None, None]:
        # pyright: ignore
        """Recursively traverse a directory tree starting from the given path.

        Yields
        ------
            Generator[os.DirEntry]
        """
        cdef str path = self.path if root is None else root
        with os.scandir(path) as entries:
            for entry in entries:
                try:
                    if entry.is_file(follow_symlinks=follow_symlinks): # type: ignore
                        yield entry
                    elif entry.is_dir(follow_symlinks=follow_symlinks): # type: ignore
                        yield from self.traverse(root=entry.path, follow_symlinks=follow_symlinks)
                        yield entry
                except PermissionError:
                    continue
    def filter(self, str ext) -> list[Base]:
        """Filter files by extension."""
        return [obj(item.path) for item in filter(lambda x: x.name.endswith(ext), self.traverse())]

    def glob(self, str pattern) -> list[Base]:
        """Filter files by glob pattern."""
        return [obj(item.path) for item in filter(lambda x: fnmatch.fnmatch(x.name, pattern), self.traverse())]

    def __getitem__(self, str key, /) -> list[Base]:
        """Get a file by name."""
        return [_obj(item.path) for item in self.ls() if item.name == key]


    def __format__(self, str format_spec, /) -> str:
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

    def __hash__(self) -> int:
        return hash((tuple(self.content), self.is_empty()))

    def __len__(self) -> int:
        """Return the number of items in the object."""
        return len(list(self.traverse()))

    def __contains__(self, item: Base) -> bint:
        sha = item.sha256()
        if isinstance(sha, bytes):
            sha = sha.decode()
        return sha in self.db # type: ignore


    def __iter__(self) -> Iterator[Base]:
        """Yield a sequence of Base instances for each item in self."""
        cdef unicode root, directory
        cdef list[str] _, files
        for root, _, files in os.walk(self.path):
            # Yield directories first to avoid unnecessary checks inside the loop
            for directory in _:
                cls_instance = Dir.__new__(Dir, os.path.join(root, directory))
                yield cls_instance
            for file in files:
                try:
                    cls_instance = _obj(os.path.join(root, file))
                    yield cls_instance
                except FileNotFoundError as e:
                    print(f"DirNode.Dir.__iter__(): {e!r}")

    def __eq__(self, other: "Dir", /) -> bint:
        """Compare the contents of two Dir objects."""
        return all(
            (
                isinstance(other, self.__class__),
                hash(self) == hash(other),
            ),
        ) # type: ignore

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name}, size={self.size_human}, is_empty={self.is_empty()})"# type: ignore

cdef inline Base _obj(str path):
    """Return a Base object for the given path."""
    cdef unicode ext, file_type
    cdef tuple[str] extensions
    cdef str class_name
    cdef object FileClass
    cdef object module

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
                return FileClass.__new__(FileClass, path) # type: ignore
            except FileNotFoundError as e:
                print(f"{e!r}")
            except AttributeError:
                class_name = 'Base'
                return Base.__new__(Base, path) # type: ignore
    try:
        FileClass = Base.__new__(Base, path) # type: ignore
    except FileNotFoundError as e:
        return None # type: ignore
    return Base.__new__(Base, path) # type: ignore

class File:
    def __new__(cls, filepath, /, init=False):
        # Dynamically create the class name and instantiate it
        cls = _obj(filepath)
        if init:
            cls.__init__(filepath)
        return cls

    @staticmethod
    def from_hash(hash: str, db: dict[str, set[str]]) -> list[Base]:
        return [_obj(path) for path in db[hash]]

cpdef Base obj(str file_path):
    """Return a Base instance for the given file path."""
    return _obj(file_path)


cdef int stat_result(item):
    return item[1]
