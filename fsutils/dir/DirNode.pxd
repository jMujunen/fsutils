from fsutils.file.GenericFile cimport File
"""Represents a directory. Contains methods to list objects inside this directory."""

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
        - `objects`     : Read-only property yielding a sequence of DirectoryObject or FileObject instances
        - `directories` : Read-only property yielding a list of absolute paths for subdirectories

    """
    cdef public str _pkl_path
    cdef public unsigned long int _size
    cdef public dict[str, list[str]] _db

    cpdef list[File] fileobjects(self)
    cpdef list videos(self)
    cpdef list images(self)
    cpdef tuple[set[str], set[str]] compare(self, Dir other)
    cpdef list[File] non_media(self)
    cpdef dict[str, int] describe(self, bint print_result=?)
    cpdef dict[str, list[str]] serialize(self, bint replace=?, bint progress_bar=?)

cdef inline File _obj(str path)

cpdef File obj(str file_path)
cdef inline (char*, char*) worker(File item)

