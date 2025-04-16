from Cython.Build import cythonize
from setuptools import setup
from setuptools.extension import Extension

openssl_include = "/usr/include/openssl"
openssl_lib = "/usr/lib"

ext_modules = [
    Extension(
        "fsutils.dir.DirNode",
        ["fsutils/dir/DirNode.pyx"],
        include_dirs=[openssl_include],
        libraries=["ssl", "crypto"],
        library_dirs=[openssl_lib],
        extra_compile_args=["-DCYTHON_FAST_GIL", "-ffast-math", "-O3", "-Wall", "-Wextra"],
    ),
    Extension(
        "fsutils.file.GenericFile",
        ["fsutils/file/GenericFile.pyx"],
        include_dirs=[openssl_include],
        libraries=["ssl", "crypto"],
        library_dirs=[openssl_lib],
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
