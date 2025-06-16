class FFProbeError(Exception):
    pass


class DurationError(Exception):
    pass


class CorruptMediaError(Exception):
    def __init__(self, filepath: str) -> None:
        super().__init__(f"{filepath} is corrupt")
