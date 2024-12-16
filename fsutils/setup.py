from Cython.Build import cythonize
from setuptools import setup

setup(ext_modules=cythonize(
    ["dir/DirNode.pyx",
    "file/GenericFile.pyx",
    "dev/_FFProbe.pyx"]
))
