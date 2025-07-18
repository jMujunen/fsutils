"""Base class and building block for all other classes defined in this library."""
import re
cimport cython
GIT_OBJECT_REGEX: re.Pattern
from libc.stdint cimport uint8_t

cdef extern from "hash.c":
    ctypedef struct sha256_hash_t:
        uint8_t _hash[32]

    sha256_hash_t * returnHash(const char *filePath) noexcept nogil


cdef class Base:
    """This is the base class for all of the following objects.

    It represents a generic file and defines the common methods that are used by all of them.

    It can be used standlone (Eg. text based files) or as a parent class for other classes.

    Attributes
    ----------
        - `encoding (str)` : The encoding to use when reading/writing the file. Defaults to utf-8.
        - `path (str)` : The absolute path to the file.

    Properties:
    ----------
        - `path` : The absolute path to the file.
        - `encoding` : The encoding of the file.


        - `size` : The size of the file in bytes.
        - `size_human` : The size of the file in a human readable format.

    Methods
    ----------
        - `read_text()` : Return the contents of the file as a string
        - `read_json()` : Return the contents of the file as a json object

        - `is_image()` : Check if item is an image
        - `is_video()` : Check if item is a video
        - `is_gitobject()` : Check if item is a git object
        - `is_dir()` : Check if the file is a directory
        - `exists()` : Check if the file exists

        - `detect_encoding()` : Return the encoding of the file based on its content

        - `times()` : Return a tuple with (atime, mtime, ctime) of the file.
        - `mtime()` : Return the last modified time of the file
        - `ctime()` : Return the creation time of the file
        - `atime()` : Return the last access time of the file

        - `head(self, n=5)` : Return the first n lines of the file
        - `tail(self, n=5)` : Return the last n lines of the file
        - `__eq__()` : Compare properties of FileObjects
        - `__str__()` : Return a string representation of the object

    """
    cdef str _suffix, _stem
    cdef public str path, encoding





