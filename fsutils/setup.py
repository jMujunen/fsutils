from Cython.Build import cythonize
from setuptools import setup
from setuptools.extension import Extension

ext_modules = [
    Extension(
        "*",
        ["**/*.pyx"],
        libraries=["m"],
        extra_compile_args=["-ffast-math", "-O3", "-Wall", "-Wextra"],
    )
]

setup(
    name="fsutils",
    ext_modules=cythonize(ext_modules),
)

# setup(ext_modules=cythonize(["**/*.pyx"]))
