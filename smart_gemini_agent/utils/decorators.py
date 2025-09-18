"""
Декораторы для Smart Gemini Agent
"""

import asyncio
import logging
import re
from functools import wraps
from typing import Callable, Any, AsyncGenerator

logger = logging.getLogger(__name__)


def retry_on_failure(max_retries: int = 2, delay: float = 1.0):
    """
    Декоратор для повторения асинхронных операций при неудаче.
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    error_text = str(e)
                    
                    if "429" in error_text or "ResourceExhausted" in error_text:
                        retry_secs = None
                        m = re.search(r"retry_delay\s*{\s*seconds:\s*(\d+)", error_text)
                        if m:
                            retry_secs = int(m.group(1))
                        
                        wait_time = retry_secs if retry_secs else delay
                        logger.warning(f"Превышены лимиты API (429). Попытка {attempt + 1} неудачна, повтор через {wait_time}с")
                        await asyncio.sleep(wait_time)
                    elif attempt < max_retries - 1:
                        logger.warning(f"Попытка {attempt + 1} неудачна, повтор через {delay}с")
                        await asyncio.sleep(delay)
                    else:
                        raise e
            if last_exception:
                raise last_exception
        return wrapper
    return decorator


def retry_on_failure_async_gen(max_retries: int = 2, delay: float = 1.0):
    """
    Декоратор для повторения операций асинхронного генератора при неудаче.
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> AsyncGenerator[Any, None]:
            last_exception = None
            for attempt in range(max_retries):
                try:
                    async for item in func(*args, **kwargs):
                        yield item
                    return
                except Exception as e:
                    last_exception = e
                    error_text = str(e)
                    
                    if "429" in error_text or "ResourceExhausted" in error_text:
                        retry_secs = None
                        m = re.search(r"retry_delay\s*{\s*seconds:\s*(\d+)", error_text)
                        if m:
                            retry_secs = int(m.group(1))
                        
                        wait_time = retry_secs if retry_secs else delay
                        logger.warning(f"Превышены лимиты API (429). Попытка {attempt + 1} неудачна, повтор через {wait_time}с")
                        await asyncio.sleep(wait_time)
                    elif attempt < max_retries - 1:
                        logger.warning(f"Попытка {attempt + 1} неудачна, повтор через {delay}с")
                        await asyncio.sleep(delay)
                    else:
                        raise e
            if last_exception:
                raise last_exception
        return wrapper
    return decorator