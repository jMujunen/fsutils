"""Benchmarks for directory operations."""

from typing import Any
from fsutils.dir import Dir
from rich.table import Table, box
from rich.console import Console
from ExecutionTimer import ExecutionTimer
from decorators import exectimer
# from typing import GeneratorType


class Benchmark:
    def __init__(self, dirObj: Dir) -> None:
        """Initialize the benchmark object with a given directory path."""
        self.dir = dirObj
        self.results = []

    def _methods(self, suppress_errors=True):
        methods = []
        kwargs = {}
        for name in dir(self.dir):
            # Ignore private and built-in attributes
            if not name.startswith("!"):
                try:
                    val = getattr(self.dir, name)
                    # If the attribute has a __call__ method, it's probably callable
                    if callable(val) or isinstance(val, property):
                        methods.append((name, getattr(self.dir, name)()))
                except Exception as e:
                    # Ignore any errors when calling the attribute
                    if suppress_errors:
                        continue
                    print(f"Error calling {self.dir.__class__.__name__}.{name}: {e}")
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
        with ExecutionTimer(print_on_exit=False) as timer:
            try:
                getattr(self.dir, method_name)(**kwargs)  # Call the method on the Dir object
            except Exception as e:
                print(f"Error calling {self.dir.__class__.__name__}.{method_name}: {e}")
        self.results.append((method_name, timer))

    def _benchmark_generator(self, generator_name: str) -> None:
        """Benchmark the specified generator of DirNode.Dir."""
        with ExecutionTimer(print_on_exit=False) as timer:
            list(getattr(self.dir, generator_name)())  # Call the generator on the Dir object
        self.results.append((generator_name, timer))

    def print_results(self) -> None:
        """Print the benchmarking results in a formatted table."""
        console = Console()
        table = Table(title=self.dir.path)

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
        "file_objects": {},
        "videos_": {},
        "images_": {},
        "describe": {"print_result": False},
        "serialize": {"progress_bar": False},
        "duplicates": {},
    }
    generators = {"__iter__": {}, "traverse": {}, "videos": {}, "objects": {}}

    dirs = [
        Dir(i) for i in {"/mnt/ssd/Media/", "/home/joona/Code", "/home/joona/Pictures/RuneLite/"}
    ]
    with ExecutionTimer(print_on_exit=False) as total:
        for d in dirs:
            benchmark = Benchmark(d)
            print(d.path)
            # result = benchmark._methods(suppress_errors=True)
            result = benchmark.execute(methods, generators)
            print("-" * 100)

    print(f"Total time: {total!s}")
