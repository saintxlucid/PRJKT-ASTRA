"""
Exception handling utilities for the plugin system.
"""
from __future__ import annotations

import asyncio
import functools
import inspect
import logging
import sys
import traceback
from typing import Any, Callable, Optional, TypeVar, cast

import structlog
from .exceptions import PluginError

logger = structlog.get_logger()

F = TypeVar("F", bound=Callable[..., Any])

def handle_plugin_errors(
    default_return: Any = None,
    reraise: bool = False,
    log_level: int = logging.ERROR
) -> Callable[[F], F]:
    """
    Decorator to handle plugin-related exceptions gracefully.
    
    Args:
        default_return: Value to return on error if not reraising
        reraise: Whether to reraise the caught exception
        log_level: Logging level for error messages
        
    Returns:
        Decorated function
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
            except PluginError as e:
                logger.log(
                    log_level,
                    f"Plugin error in {func.__name__}",
                    error=str(e),
                    traceback=traceback.format_exc()
                )
                if reraise:
                    raise
                return default_return
            except Exception as e:
                logger.log(
                    log_level,
                    f"Unexpected error in {func.__name__}",
                    error=str(e),
                    traceback=traceback.format_exc()
                )
                if reraise:
                    raise
                return default_return
                
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return await func(*args, **kwargs)
            except PluginError as e:
                logger.log(
                    log_level,
                    f"Plugin error in {func.__name__}",
                    error=str(e),
                    traceback=traceback.format_exc()
                )
                if reraise:
                    raise
                return default_return
            except Exception as e:
                logger.log(
                    log_level,
                    f"Unexpected error in {func.__name__}",
                    error=str(e),
                    traceback=traceback.format_exc()
                )
                if reraise:
                    raise
                return default_return
                
        return cast(F, async_wrapper if inspect.iscoroutinefunction(func) else sync_wrapper)
        
    return decorator

def format_exception(e: Exception) -> str:
    """
    Format an exception with its traceback for logging.
    
    Args:
        e: Exception to format
        
    Returns:
        Formatted error message with traceback
    """
    return "".join(traceback.format_exception(type(e), e, e.__traceback__))

async def run_with_error_handling(
    func: Callable[..., Any],
    *args: Any,
    default_return: Any = None,
    reraise: bool = False,
    log_level: int = logging.ERROR,
    **kwargs: Any
) -> Any:
    """
    Run a function with standardized error handling.
    
    Args:
        func: Function to run
        *args: Positional arguments for func
        default_return: Value to return on error if not reraising
        reraise: Whether to reraise caught exceptions
        log_level: Logging level for error messages
        **kwargs: Keyword arguments for func
        
    Returns:
        Function result or default_return on error
    """
    try:
        if inspect.iscoroutinefunction(func):
            return await func(*args, **kwargs)
        else:
            return func(*args, **kwargs)
    except PluginError as e:
        logger.log(
            log_level,
            f"Plugin error in {func.__name__}",
            error=str(e),
            traceback=format_exception(e)
        )
        if reraise:
            raise
        return default_return
    except Exception as e:
        logger.log(
            log_level,
            f"Unexpected error in {func.__name__}",
            error=str(e),
            traceback=format_exception(e)
        )
        if reraise:
            raise
        return default_return