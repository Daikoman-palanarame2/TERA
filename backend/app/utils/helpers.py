"""
Module: backend/app/utils/helpers
Purpose:
    Provides common utility functions for async context management (run_in_executor) 
    and string normalizations.
"""

import asyncio
import functools
from typing import Callable, TypeVar, Any

T = TypeVar("T")

async def run_in_executor(func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
    """Runs a CPU-bound or blocking synchronous function inside the event loop executor.

    This ensures that blocking operations (such as ONNX model runs, filesystem tasks, 
    or database writes) do not freeze the main asyncio event loop.

    Args:
        func: The synchronous callable function to execute.
        *args: Positional arguments to pass to the function.
        **kwargs: Keyword arguments to pass to the function.

    Returns:
        T: The evaluated return value of the function.
    """
    loop = asyncio.get_running_loop()
    if kwargs:
        # run_in_executor only supports positional arguments; wrap kwargs using partial
        partial_func = functools.partial(func, **kwargs)
        return await loop.run_in_executor(None, partial_func, *args)
    return await loop.run_in_executor(None, func, *args)


def clean_prompt(prompt: str) -> str:
    """Standardizes, normalizes, and trims a raw prompt query string.

    Args:
        prompt: The raw user prompt text.

    Returns:
        str: The trimmed, normalized prompt string.
    """
    if not prompt:
        return ""
    return prompt.strip()
