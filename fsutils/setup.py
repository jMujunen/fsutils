from Cython.Build import cythonize
from setuptools import setup

setup(ext_modules=cythonize(["**/*.pyx"]))

# setup(
#     # ext_modules=cythonize([
#         "dir/DirNode.pyx",
#         "file/GenericFile.pyx",
#         "file/__init__.pyx",
#         "dir/__init__.pyx",
#         "dev/_FFProbe.pyx",
#     ])
# )
