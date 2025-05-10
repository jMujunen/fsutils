"""Represents a directory. Contains methods to list objects inside this directory."""

from fsutils.file.GenericFile cimport Base
from libc.stdint cimport uint8_t



cdef extern from "hash.c":
    ctypedef struct sha256_hash_t:
        uint8_t _hash[32]

    struct HashMapEntry:
        char *filepath
        sha256_hash_t *sha
    struct HashMap:
        HashMapEntry *entries
        int size
    HashMap *hashDirectory(const char *directory) noexcept nogil
    char** listFilesRecursively(const char *basePath, int *count)


cdef class Dir(Base):
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
    cdef public str _pkl_path
    cdef unsigned long int _size
    cdef dict[str, set[str]] _db
