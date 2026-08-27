from __future__ import annotations

import asyncio

# ponytail: process-local by design for single-process SQLite; use the existing
# invalidation bus if cluster-wide PostgreSQL maintenance is ever required.
_paused = False
_waiters: set[asyncio.Future[None]] = set()


def pause() -> None:
    global _paused
    _paused = True


def resume() -> None:
    global _paused
    _paused = False
    waiters = tuple(_waiters)
    _waiters.clear()
    for waiter in waiters:
        if not waiter.done():
            waiter.set_result(None)


def reset() -> None:
    resume()


def is_paused() -> bool:
    return _paused


def get_waiter_count() -> int:
    return len(_waiters)


async def wait_until_resumed() -> None:
    while _paused:
        waiter = asyncio.get_running_loop().create_future()
        _waiters.add(waiter)
        try:
            await waiter
        finally:
            _waiters.discard(waiter)
