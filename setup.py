from Cython.Build import cythonize
from setuptools import setup
from setuptools.extension import Extension

ext_modules = [
    Extension(
        "fsutils.dir.DirNode",
        ["fsutils/dir/DirNode.pyx"],
        libraries=["m"],
        extra_compile_args=["-ffast-math", "-O3", "-Wall", "-Wextra"],
    ),
    Extension(
        "fsutils.file.GenericFile",
        ["fsutils/file/GenericFile.pyx"],
        libraries=["m"],
        extra_compile_args=["-ffast-math", "-O3", "-Wall", "-Wextra"],
    ),
]

setup(
    name="fsutils",
    version="0.1",
    ext_modules=cythonize(ext_modules),
    packages=["fsutils", "fsutils.dir", "fsutils.file"],
    include_package_data=True,
    zip_safe=False,
)
