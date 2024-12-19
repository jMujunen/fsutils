"""Base class and building block for all other classes defined in this library."""

import re
from datetime import datetime
# from typing import NamedTuple


GIT_OBJECT_REGEX: re.Pattern
ctypedef tuple[datetime, datetime, datetime] DatetimeTuple
# cdef NamedTuple St

cdef extern from "stdio.h":
    ctypedef ssize_t ssize_ts
    ctypedef size_t size_t
    ctypedef int FILE
    cdef FILE* fopen(const char* filename, const char* mode)
    ssize_t fread(void* ptr, size_t size, size_t nmemb, FILE* stream)
    int fclose(FILE* stream)


cdef class File:
    cdef public str _suffix
    cdef public str _stem
    cdef public str path
    cdef public str encoding
    cdef list[str] head(File, unsigned short int n = ?)
    cdef list[str] tail(File, unsigned short int n = ?)
    cdef stat(File)
    cdef bint is_binary(File)
    cdef bint is_gitobject(File)
    cdef bint is_image(File)
    cdef bint is_video(File)
    cdef DatetimeTuple times(File)
    cdef bint exists(File)
    cdef str detect_encoding(File)
    cdef str md5_checksum(File, unsigned int chunk_size=?)
    cpdef str read_text(File)
    cpdef str sha256(File, unsigned int chunk_size=?)
    cpdef bytes _read_chunk(File, unsigned int size=?, str spec=?)


cdef c_read_chunk(File self, unsigned int size=?)

