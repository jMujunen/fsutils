from Cython.Build import cythonize
from setuptools import setup

setup(ext_modules=cythonize(
    ["dir/DirNode.pyx",
    "dir/_DirNode.pyx",
    "file/GenericFile.pyx",
    "file/_GenericFile.pyx",]
))
