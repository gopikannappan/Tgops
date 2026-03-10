"""Rate limiting utilities with Gaussian jitter for human-like timing."""

import asyncio
import random

BATCH_SIZE = 20


async def human_delay(base: float = 2.5) -> None:
    """
    Gaussian jitter delay to simulate human-like timing.

    Delay is sampled from N(base, (base*0.25)^2) and clamped to [0.5, base*3].
    """
    delay = random.gauss(base, base * 0.25)
    delay = max(0.5, min(delay, base * 3))
    await asyncio.sleep(delay)


async def emergency_delay(base: float = 1.0) -> None:
    """
    Minimal delay for emergency operations.

    1.0s default floor — community-documented safe threshold for ban/kick
    calls is ~30/minute. Delay is base +/- 0.15s, clamped to minimum of 0.5s.
    If FLOOD_WAIT triggers at 1.0s, raise to 1.5s via config.
    """
    delay = max(0.5, base + random.uniform(-0.15, 0.15))
    await asyncio.sleep(delay)


async def batch_delay() -> None:
    """Additional delay inserted every BATCH_SIZE operations to avoid rate limits."""
    await asyncio.sleep(random.uniform(30, 60))
