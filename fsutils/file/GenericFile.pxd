"""Base class and building block for all other classes defined in this library."""
import re
cimport cython
GIT_OBJECT_REGEX: re.Pattern
from libc.stdint cimport uint8_t

cdef extern from "hash.c":
    ctypedef struct sha256_hash_t:
        uint8_t hash[32]

    sha256_hash_t * returnHash(const char *filePath) noexcept nogil


cdef class File:
    cdef str _suffix
    cdef str _stem
    cdef public str path
    cdef public str encoding
    cpdef list[str] head(File, unsigned short int n = ?)
    cpdef list[str] tail(File, unsigned short int n = ?)
    cpdef str read_text(File)
    cpdef object read_json(File)

