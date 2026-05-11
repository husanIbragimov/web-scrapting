import asyncio
import logging
from typing import Any, Callable, Awaitable, Optional

logger = logging.getLogger(__name__)

async def async_retry(
    fn: Callable[[], Awaitable[Any]],
    retries: int = 3,
    backoff_base: float = 2.0,
    args: tuple = (),
    kwargs: dict = None,
) -> Optional[Any]:
    """Call async fn with exponential backoff. Returns None if all retries fail."""
    if kwargs is None:
        kwargs = {}
    for attempt in range(retries):
        try:
            return await fn(*args, **kwargs)
        except Exception as exc:
            wait = backoff_base ** attempt
            logger.warning(f"Attempt {attempt + 1}/{retries} failed: {exc}. Retrying in {wait:.1f}s")
            if attempt < retries - 1:
                await asyncio.sleep(wait)
    logger.error(f"All {retries} retries exhausted for {fn.__name__}")
    return None
