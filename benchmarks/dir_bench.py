"""Benchmarks for directory operations."""

from typing import Any
from fsutils.dir import Dir
from rich.table import Table, box
from rich.console import Console
from ExecutionTimer import ExecutionTimer
from decorators import exectimer
# from typing import GeneratorType


class Benchmark:
    def __init__(self, dirpath: str) -> None:
        """Initialize the benchmark object with a given directory path."""
        self.dirpath = dirpath
        self.results = []

    def _methods(self, suppress_errors=True):
        dirObj = Dir(self.dirpath)
        methods = []
        kwargs = {}
        for name in dir(dirObj):
            # Ignore private and built-in attributes
            if not name.startswith("!"):
                try:
                    val = getattr(dirObj, name)
                    # If the attribute has a __call__ method, it's probably callable
                    if callable(val):
                        methods.append((name, getattr(dirObj, name)()))
                    elif isinstance(val, property):
                        methods.append((name, getattr(dirObj, name)))
                except Exception as e:
                    # Ignore any errors when calling the attribute
                    if suppress_errors:
                        continue
                    print(f"Error calling {dirObj.__class__.__name__}.{name}: {e}")
        return methods

    def execute(
        self,
        methods: dict[str, dict[str, Any]],
        generators: dict[str, dict[str, Any]] | None = None,
    ) -> None:
        for method, kwargs in methods.items():
            self._benchmark_method(method, **kwargs)
        if generators is not None:
            for generator in generators:
                self._benchmark_generator(generator)
        self.print_results()

    def _benchmark_method(self, method_name: str, **kwargs) -> None:
        """Benchmark the specified method of DirNode.Dir."""
        dirObj = Dir(self.dirpath)
        with ExecutionTimer(print_on_exit=False) as timer:
            try:
                getattr(dirObj, method_name)(**kwargs)  # Call the method on the Dir object
            except TypeError:
                getattr(dirObj, method_name)
            except Exception as e:
                print(f"Error calling {dirObj.__class__.__name__}.{method_name}: {e}")
        self.results.append((method_name, timer))

    def _benchmark_generator(self, generator_name: str) -> None:
        """Benchmark the specified generator of DirNode.Dir."""
        dirObj = Dir(self.dirpath)
        with ExecutionTimer(print_on_exit=False) as timer:
            list(getattr(dirObj, generator_name)())  # Call the generator on the Dir object
        self.results.append((generator_name, timer))

    def print_results(self) -> None:
        """Print the benchmarking results in a formatted table."""
        console = Console()
        table = Table(title=self.dirpath)

        # Add columns to the table
        table.add_column("Method", style="cyan")
        table.add_column("Elapsed Time (s)", style="magenta")

        # Populate the table with the benchmark data
        for method, elapsed_time in sorted(self.results):
            table.add_row(method, f"{elapsed_time!s}")

        # Print the table
        console.print(table)


if __name__ == "__main__":
    methods = {
        "__repr__": {},
        "describe": {"print_result": False},
        "serialize": {"progress_bar": False},
        "duplicates": {},
        "size_human": {},
    }
    generators = {
        "__iter__": {},
        "traverse": {},
    }

    dirs = {"/mnt/ssd/Media/", "/home/joona/Code"}
    with ExecutionTimer(print_on_exit=False) as total:
        for d in dirs:
            benchmark = Benchmark(d)
            print(d)
            result = benchmark.execute(methods, generators)
            print("-" * 100)
    print(f"Total: {total!s}")
