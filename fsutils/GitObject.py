"""Represents a git object."""

from .GenericFile import File


class Git(File):
    """Represents a git object."""

    def __init__(self, path: str) -> None:
        """Init git object."""
        super().__init__(path, encoding="iso-8859-1")

    def decode(self) -> list[str]:
        """Decode the object from bytes to str."""
        if self.content is not None:
            return [i.decode("iso-8859-1").strip() for i in self.content]
        return []
