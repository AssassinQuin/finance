from collections.abc import Coroutine
from typing import Any, TypeVar

import typer

from ..infra.http_client import http_client, run_async
from .presenter import ConsolePresenter

T = TypeVar("T")


def run_command(coro: Coroutine[Any, Any, T], error_msg: str) -> T:
    try:
        return run_async(coro)
    except Exception as e:
        ConsolePresenter.print_error(f"{error_msg}: {e}")
        raise typer.Exit(1) from e
    finally:
        run_async(http_client.close())
