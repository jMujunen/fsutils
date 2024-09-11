"""Represents a directory. Contains methods to list objects inside this directory."""

import datetime
import os
import sys
from collections import defaultdict
from collections.abc import Iterator

from size import Size
from ThreadPoolHelper import Pool

from fsutils.GenericFile import File
from fsutils.GitObject import Git
from fsutils.ImageFile import Img
from fsutils.LogFile import Log
from fsutils.mimecfg import FILE_TYPES
from fsutils.ScriptFile import Exe
from fsutils.VideoFile import Video


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

    def __init__(self, path: str = "./") -> None:
        """Initialize a new instance of the Dir class.

        Parameters
        ----------
            - `path (str)` : The path to the directory.
        """
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
        """Return a list of subdirectory paths relative to the directory represented by this object."""
        return [f".{folder.path.replace(self.path, "")}" for folder in self.dirs]

    @property
    def objects(self) -> list[File]:
        """Return a list of fsutil objects inside self."""
        if not self._objects:
            self._objects = list(self.__iter__())
        return self._objects

    def file_info(self, file_name: str) -> File | None:
        """Query the object for files with the given name.

        Return an instance of the appropriate subclass of File if a matching file is found."""
        try:
            if file_name in os.listdir(self.path):
                return obj(os.path.join(self.path, file_name))
        except (NotADirectoryError, FileNotFoundError):
            pass
        for d in self.dirs:
            content = os.listdir(os.path.join(self.path, d.path))
            if file_name in content:
                return obj(os.path.join(self.path, d.path, file_name))
        return None

    def query_image(self, image: Img, threshold=10, method="phash") -> list[Img]:
        """Scan self for images with has values similar to the one of the given image."""
        pool = Pool()
        similar_images = []

        def hash_extracter(img: Img, method: str):
            abs(hash_to_query - img.calculate_hash(method))
            return img.calculate_hash(method), img

        hash_to_query = image.calculate_hash(method)
        for result in pool.execute(hash_extracter, self.images, method, progress_bar=True):
            if result:
                h, img = result
                try:
                    distance = abs(hash_to_query - h)
                    print(distance, end="\r")
                    if distance < threshold:
                        similar_images.append((img, threshold))
                        print(f"\n\033[1;33m{img.basename}\033[0m")
                except Exception:
                    print("\033[31mError while calculating hash difference: {e!r}\033[0m")
        return similar_images

    @property
    def is_dir(self) -> bool:
        """Is the object a directory?."""
        return os.path.isdir(self.path)

    @property
    def is_empty(self) -> bool:
        """Check if the directory is empty."""
        return len(self.files) == 0

    @property
    def images(self) -> list[Img]:
        """A list of ImageObject instances found in the directory."""
        return [item for item in self if isinstance(item, Img)]

    @property
    def videos(self) -> list[Video]:
        """A list of VideoObject instances found in the directory."""
        return [item for item in self if isinstance(item, Video)]

    @property
    def dirs(self) -> list[File]:
        """A list of DirectoryObject instances found in the directory."""
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
        max_key_length = max([len(k) for k in sorted_stat])
        for key, value in sorted_stat.items():
            print(f"{key: <{max_key_length}} {value}")

    @property
    def size(self) -> Size:
        """Return the total size of all files and directories in the current directory."""
        if "_size" in self.__dict__:
            return self.__dict__["_size"]

        def _(file: File) -> int:
            return file.size

        pool = Pool()
        return Size(sum(pool.execute(_, self.file_objects, progress_bar=False)))

    @property
    def size_human(self) -> str:
        return str(self.size)

    @staticmethod
    def detect_duplicates():
        """Detect duplicate files in a directory and its subdirectories."""

    def sort(self, specifier: str, reverse=True) -> list[str]:
        """Sort the files and directories by the specifying attribute."""

        specs = {
            "mtime": lambda x: datetime.datetime.fromtimestamp(os.stat(x.path).st_mtime).strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
            "ctime": lambda x: datetime.datetime.fromtimestamp(os.stat(x.path).st_ctime).strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
            "atime": lambda x: datetime.datetime.fromtimestamp(os.stat(x.path).st_atime).strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
            "size": lambda x: x.size,
            "name": lambda x: x.basename,
            "ext": lambda x: x.extension,
        }
        _fmt = []
        for file in self.file_objects:
            _fmt.append((specs.get(specifier, "mtime")(file), file.path))

        result = sorted(_fmt, key=lambda x: x[0], reverse=reverse)

        # # Print the table
        format_string = "{:<25}{:<40}"
        print(format_string.format(specifier, "File"))
        for f in result:
            print(format_string.format(*f))
        return result

    def __format__(self, format_spec: str, /) -> str:
        pool = Pool()
        if format_spec == "videos":
            print(Video.fmtheader())
            return "\n".join(
                result for result in pool.execute(format, self.videos, progress_bar=False)
            )
        if format_spec == "images":
            print(Img.fmtheader())
            return "\n".join(
                result for result in pool.execute(format, self.images, progress_bar=False)
            )
        return "Formatting Dir is not supported yet"

    def __contains__(self, item: File) -> bool:
        """Is `File` in self?"""  # noqa
        return item in self.file_objects or item in self.dirs if isinstance(item, File) else False

    def __hash__(self) -> int:
        return hash((tuple(self.content), self.stat, self.is_empty))

    def __len__(self) -> int:
        """Return the number of items in the object."""
        return len(self.objects)

    def __iter__(self) -> Iterator[File]:
        """Yield a sequence of File instances for each item in self."""
        for root, _, files in os.walk(self.path):
            # Yield directories first to avoid unnecessary checks inside the loop
            for directory in _:
                yield Dir(os.path.join(root, directory))

            for file in files:
                path = os.path.join(root, file)  # full path of the file
                _obj = obj(path)
                if _obj:
                    yield _obj

    def __eq__(self, other: "Dir", /) -> bool:
        """Compare the contents of two Dir objects."""
        return all(
            (
                isinstance(other, self.__class__),
                self.exists,
                other.exists,
                hash(self) == hash(other),
            )
        )

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}(size={self.size_human}, is_empty={self.is_empty})".format(
                **vars(self)
            )
        )


def obj(path: str) -> File | None:
    """Return a File object for the given path."""
    if not os.path.exists(path):
        return None
    if os.path.isdir(path):
        return Dir(path)
    _, ext = os.path.splitext(path.lower())

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
    # If no match is found, return a default instance
    try:
        FileClass = File(path)
    except FileNotFoundError as e:
        print(f"{e!r}")
        return None
    return File(path)
