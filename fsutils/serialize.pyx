import cython
from ThreadPoolHelper import Pool
import pickle
from DirNode import Dir
from typing import  Generator


cdef tuple helper (file):
    cdef str name, path, sha
    path, sha = file.path, file.sha256()

    return sha, path

cpdef serialize (self) :
    """Create an hash index of all files in self."""
    cdef dict[int,list[str]] db = {}
    cdef tuple result
    file_objects = self.file_objects

    if self._pkl_path.exists():
        self._pkl_path.unlink()

    pool = Pool()
    self.db = {}
    for result in pool.execute(
        helper,
        file_objects,
        progress_bar=True,
    ):
        if result:
            sha, path = result
            if sha not in self.db:
                self.db[sha] = [path]
            else:
                self.db[sha].append(path)
    self._pkl_path.write_bytes(pickle.dumps(self.db))
    db = self.db
    return db
