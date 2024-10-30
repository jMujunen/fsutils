import pickle

import cython
from ThreadPoolHelper import Pool


# @cython.boundscheck(False)
# @cython.wraparound(False)
def serialize(self):
    """Create an hash index of all files in self."""
    # _result: cython.tuple
    # _file_objects: cython.list
    # db = cython.dict

    # cdef dict[int,list[str]] db = {}
    # cdef tuple result
    # cdef list file_objects
    file_objects = self.file_objects

    if self._pkl_path.exists():
        self._pkl_path.unlink()
    # else self._pkl_path.exists() and replace is False:
    # return self.load_database()

    pool = Pool()

    for result in pool.execute(
        lambda x: (x.sha256(), x.path),
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
    return self.db
