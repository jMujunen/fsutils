import subprocess
import json
cdef class FFStream:
    """A stream in a media file"""
    cdef dict __dict__
    def __init__(self, dict index) -> None:
        """Create an stream instance from a dictionary"""
        self.__dict__ = index
        for k, v in self.__dict__.items():
            setattr(self, k, v)

cdef class FFprobe:
    cdef public str path
    cdef char* error
    cdef public dict[str, str] result
    cdef public FFStream video, audio

    def __init__(self, str path):
        cdef list streams
        cdef dict stream

        self.path = path
        self.result, self.error = self.run()
        streams = self.result.get('streams', [])
        for stream in streams:
            stream_type = stream['codec_type']
            if stream_type == 'audio':
                    self.audio = FFStream(stream)
            elif stream_type =='video':
                    self.video = FFStream(stream)
            else:
                print('Unexpected: ',stream_type, '\n\t', stream)

    def __str__(self):
        return json.dumps(self.result, indent=4)

    cdef tuple[dict, char*] run(self):
        cdef bytes output
        cdef bytes error
        cdef str cmd = "ffprobe -print_format json -show_streams '{}' -v error"

        with subprocess.Popen(cmd.format(self.path),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,shell=True) as p: # type: ignore
            output, error = p.communicate()
        return json.loads(output.decode('utf-8')), error

