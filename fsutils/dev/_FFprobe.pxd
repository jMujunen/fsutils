cdef class FFprobe:
    cdef public str path
    cdef char* error
    cdef public dict[str, str] result, video, audio

    def __init__(self, str path) -> None: ...
    def __str__(self) -> str: ...

    cdef tuple[dict, char*] run(self)
