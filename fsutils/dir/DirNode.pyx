"""Represents a directory. Contains methods to list objects inside this directory."""
import os
import pickle
import sys
from collections import defaultdict
import subprocess
from pathlib import Path
from typing import Optional, Iterator, Generator
import os
from cpython cimport bool
from cython cimport nogil

from ThreadPoolHelper import Pool

from fsutils.img import Img
from fsutils.log import Log
from fsutils.utils.mimecfg import FILE_TYPES
from fsutils.video import Video
from fsutils.utils.tools  import format_bytes
from fsutils.file.GenericFile cimport File
cdef class Dir(File):
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
        - `dirs` : Read-only property yielding a list of absolute paths for subdirectories

    """

    def __init__(self, path: Optional[str] = None, bool mkdir=False) -> None: # type: ignore
        """Initialize a new instance of the Dir class.

        Parameters
        ----------
            path (str) : The path to the directory.

        """
        if not path:
            path = './'

        if not os.path.exists(os.path.expanduser(path)):
            if mkdir:
                os.makedirs(os.path.expanduser(path))
            else:
                raise FileNotFoundError(f"Directory {path} does not exist")
        super().__init__(path) #type: ignore

        self._pkl_path = str(Path(self.path, f".{self.prefix.removeprefix('.')}.pkl")) # type: ignore

        depreciated_pkl = Path(self.path, f"{self.name.removeprefix('.')}.pkl") # type: ignore

        if depreciated_pkl.exists():
            depreciated_pkl.rename(self._pkl_path)
            print(f"Renamed \033[33m{depreciated_pkl.name}\033[0m -> {self._pkl_path}")

        self._db = pickle.loads(Path(self._pkl_path).read_bytes()) if Path(Path(self._pkl_path)).exists() else {}

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
                return False # type: ignore
        except StopIteration:
            return True # type: ignore
        return False # type: ignore

    cpdef list videos(self):
        cdef tuple[str] valid_exts = FILE_TYPES['video']
        return [Video(file) for file in self.ls_files() if file.lower().endswith(valid_exts)]

    cpdef list images(self):
        cdef tuple[str] valid_exts = FILE_TYPES['img']
        return [Img(file) for file in self.ls_files() if file.lower().endswith(valid_exts)]

    cpdef list[File] non_media(self):
        """Return a generator of all files that are not media."""
        cdef tuple[str] valid_exts = (*FILE_TYPES['video'],*FILE_TYPES['img'])
        return [File(file) for file in self.ls_files() if not file.lower().endswith(valid_exts)] # type: ignore

    cpdef list fileobjects(self):
        """Return a generator of all file objects."""
        return [obj(file) for file in self.ls_files()] # type: ignore

    cdef inline unsigned int stat_filter(self, dictitem):
        cdef unicode key
        cdef unsigned int value
        key, value = dictitem
        return value

    cpdef dict[str,int] describe(self, bool print_result=True):  # type: ignore
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


        sorted_stat = dict(sorted(file_types.items(), key=self.stat_filter))
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


    # @property
    # def db(self):
        # if not self._db:
            # self._db = self.load_database()
        # else:
            # return self._db
    @property
    def size(self) -> int:
        """Return the total size of all files and directories in the current directory."""
        if hasattr(self, "_size"):
            if self._size:
                return self._size
        awk = "awk '{ print $1 }'"
        cmd = f'du -bsx "{self.path}" | {awk}'
        self._size = int(subprocess.getoutput(cmd).splitlines()[-1])
        return self._size

    @property
    def size_human(self) -> str:
        return format_bytes(self.size)

    def duplicates(self, unsigned short int num_keep=2, bool updatedb=False) -> list[list[str]]: # type: ignore
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
        if Path(self._pkl_path).exists():
            return pickle.loads(Path(self._pkl_path).read_bytes())
        return {}


    cpdef dict[str, list[str]] serialize(self, replace=True, progress_bar=True):
        """Create an hash index of all files in self.

        Paramaters
        ----------
            - replace (bool): If True, re-calculate the hash values for all files
            - progress_bar (bool): If True, show a progress bar while calculating hashes.

        Returns
        -------
            - dict[str, list[str]]: A dictionary where the keys are hash values
             and the values are lists of file paths.

        """
        cdef (char*, char*) result
        cdef bytes _sha, _path, serialized_object
        cdef str sha
        cdef str path
        cdef dict[str,list[str]] db = {}
        self._pkl_path = self._pkl_path.lstrip('.')

        if Path(self._pkl_path).exists() and replace:
            Path(self._pkl_path).unlink()
        elif Path(self._pkl_path).exists() and replace is False:
            return self.load_database()

        pool = Pool()
        for result in pool.execute(
            worker,
            self.fileobjects(),
            progress_bar=True
        ):
            _sha, _path = result
            sha = _sha.decode('utf-8')
            path = _path.decode('utf-8')
            if not sha in db:
                db[sha] = [path]
            else:
                db[sha].append(path)

        serialized_object = pickle.dumps(db)
        with open(self._pkl_path, 'wb') as f:
            f.write(serialized_object)

        return db


    def compare(self, other: 'Dir') -> tuple[set[str], set[str]]:
        """Compare the current directory with another directory."""
        cdef set[str] common_files, unique_files
        cdef unsigned int num_files = len(set(self.ls_files()))
        cdef str template = '{key:<10} {color}{value:<10}{reset}{percentage}'
        cdef str green, purple, blue, reset
        green = '\033[32m'
        blue = '\033[34m'
        reset = '\033[0m'
        purple = '\033[35m'

        common_files = set(self._db.keys()) & set(other._db.keys())
        unique_files = set(self._db.keys()) - set(other._db.keys())

        print(template.format(key='Total: ',color=purple, reset=reset, value=num_files, percentage=""))
        print(template.format(key="Common: ", color=blue, reset=reset,value=len(common_files),percentage=f"{len(common_files)/num_files*100:.0f}%"))
        print(template.format(key="Unique: ", color=green, reset=reset,value=len(unique_files),percentage=f"{len(unique_files)/num_files*100:.0f}%"))

        return common_files, unique_files


    def ls(self, bool follow_symlinks=False, bool recursive=True) -> Generator[os.DirEntry, None, None]: # type: ignore
        if not recursive:
            yield from os.scandir(self.path)
        yield from self.traverse(follow_symlinks=follow_symlinks)

    def ls_dirs(self,bool follow_symlinks=False) -> Generator[str, None, None]: # type: ignore
        """Return a list of paths for all directories in self."""
        for item in self.ls():
            if item.is_dir(follow_symlinks=follow_symlinks): # type: ignore
                yield item.path

    def ls_files(self,bool follow_symlinks=False) -> Generator[str, None, None]: # type: ignore
        """Return a list of paths for all files in self."""
        for item in self.ls():
            if item.is_file(follow_symlinks=follow_symlinks): # type: ignore
                yield item.path

    def traverse(self, root=None, bool follow_symlinks=False) -> Generator[os.DirEntry, None, None]: # type: ignore
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


    def __getitem__(self, str key) -> Generator[File, None, None]:
        """Get a file by name."""
        for item in self.ls():
            if item.name == key:
                yield _obj(item.path)
        raise KeyError(f"File '{key}' not found")


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

    # def __contains__(self, File other) -> bool:
        # """Is `File` in self?"""  # noqa
        # return other.sha256() in self.db

    def __hash__(self) -> int:
        return hash((tuple(self.content), self.is_empty))

    def __len__(self) -> int:
        """Return the number of items in the object."""
        return len(list(self.traverse()))

    def __iter__(self) -> Iterator[File]:
        """Yield a sequence of File instances for each item in self."""
        cdef unicode root, directory
        cdef list[str] _, files
        for root, _, files in os.walk(self.path):
            # Yield directories first to avoid unnecessary checks inside the loop
            for directory in _:
                cls_instance = Dir(os.path.join(root, directory))
                yield cls_instance
            for file in files:
                try:
                    cls_instance = _obj(os.path.join(root, file))
                    yield cls_instance
                except FileNotFoundError as e:
                    print(f"DirNode.Dir.__iter__(): {e!r}")

    def __eq__(self, other: "Dir", /) -> bool:
        """Compare the contents of two Dir objects."""
        return all(
            (
                isinstance(other, self.__class__),
                hash(self) == hash(other),
            ),
        )
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name}, size={self.size_human}, is_empty={self.is_empty()})"# type: ignore



cdef inline File _obj(str path):
    """Return a File object for the given path."""
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
                return FileClass(path) # type: ignore
            except FileNotFoundError as e:
                print(f"{e!r}")
            except AttributeError:
                class_name = 'File'
                return File(path) # type: ignore
    try:
        FileClass = File(path) # type: ignore
    except FileNotFoundError as e:
        return None # type: ignore
    return File(path) # type: ignore


def obj(file_path: str):
    """Return a File instance for the given file path."""
    return _obj(file_path)

cdef inline (char*, char*) worker(File item):
    """Worker function to process items in parallel."""
    return item.sha256(), item.path.encode('utf-8') # type: ignore


