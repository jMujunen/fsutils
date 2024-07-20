#!/usr/bin/env python3
"""Represents a git object"""

from typing import Any, List, Tuple, Union

from .GenericFile import File


class Git(File):
    """Represents a git object"""
    def __init__(self, path: str) -> None:
        super().__init__(path, encoding='iso-8859-1')

    def decode(self) -> List[str]:
        if self.content is not None:
            return [i.decode('iso-8859-1').strip() for i in self.content]
        return []
