from typing import Any
from collections.abc import Callable
import datetime
from ExecutionTimer import ExecutionTimer


def exectimer(func: Callable[..., Any], /) -> Callable[..., Any]:
    """Measure execution time of a function."""

    def wrapper(*args, **kwargs) -> Any:
        with ExecutionTimer(print_on_exit=False) as timer:
            result = func(*args, **kwargs)
        msg = f"{func.__name__} took {timer.execution_time:.4f} seconds to execute."
        print(msg)
        return result

    return wrapper


def exectimer_wargs(*funcargs, **funckwargs):
    def dec(func, *funcargs, **funckwargs):
        print(f"\033[33m{func}, args={funcargs}, kwargs={funckwargs}\033[0m")

        def wrapper(*funcargs, **funckwargs) -> Any:
            with ExecutionTimer(print_on_exit=False) as timer:
                result = func(*funcargs, **funckwargs)
            msg = f"{func.__name__} took {timer.execution_time:.4f} seconds to execute."
            print(msg)
            return result

        return wrapper

    return dec
