import logging
from playwright_stealth import Stealth

logger = logging.getLogger(__name__)

_stealth = Stealth()

async def apply_stealth(page) -> None:
    """Apply anti-detection stealth patches to a Playwright page."""
    await _stealth.apply_stealth_async(page)
    logger.debug("Stealth applied to page")
