"""Base class and building block for all other classes defined in this library."""
import re
cimport cython

GIT_OBJECT_REGEX: re.Pattern


cdef extern from "stdio.h":
    ctypedef ssize_t ssize_ts
    ctypedef size_t size_t
    ctypedef int FILE

    cdef FILE* fopen(const char* filename, const char* mode)
    ssize_t fread(void* ptr, size_t size, size_t nmemb, FILE* stream)
    int fclose(FILE* stream)


cdef class File:
    cdef str _suffix
    cdef str _stem
    cdef public str path
    cdef public str encoding
    cpdef list[str] head(File, unsigned short int n = ?)
    cpdef list[str] tail(File, unsigned short int n = ?)

    cpdef str detect_encoding(File)
    cdef inline bytes md5_checksum(File, unsigned int chunk_size=?)
    cpdef str read_text(File)
    cpdef object read_json(File)
    cdef inline bytes _read_chunk(File, unsigned int size=?)

    cpdef bytes sha256(File)
cdef bytes c_read_chunk(File self, unsigned int size=?)

