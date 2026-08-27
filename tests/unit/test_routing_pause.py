from __future__ import annotations

import asyncio
from typing import Any, cast

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.core import routing_pause
from app.core.middleware.routing_pause import RoutingPauseMiddleware

pytestmark = pytest.mark.unit


async def _wait_for_waiters(count: int) -> None:
    async with asyncio.timeout(1):
        while routing_pause.get_waiter_count() != count:
            await asyncio.sleep(0)


@pytest.mark.asyncio
async def test_paused_http_request_waits_without_entering_the_app() -> None:
    app = FastAPI()
    app.add_middleware(cast(Any, RoutingPauseMiddleware))
    entered = asyncio.Event()

    @app.get("/v1/work")
    async def work() -> dict[str, bool]:
        entered.set()
        return {"ok": True}

    routing_pause.pause()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        request = asyncio.create_task(client.get("/v1/work"))
        await _wait_for_waiters(1)

        assert not entered.is_set()
        assert not request.done()

        routing_pause.resume()
        response = await asyncio.wait_for(request, timeout=1)

    assert response.status_code == 200
    assert response.json() == {"ok": True}


@pytest.mark.asyncio
async def test_non_proxy_routes_remain_available_while_paused() -> None:
    app = FastAPI()
    app.add_middleware(cast(Any, RoutingPauseMiddleware))

    @app.get("/api/v1/routing/status")
    async def status() -> dict[str, bool]:
        return {"paused": True}

    routing_pause.pause()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/v1/routing/status")

    assert response.status_code == 200
    assert response.json() == {"paused": True}


@pytest.mark.asyncio
async def test_cancelled_waiter_is_removed() -> None:
    routing_pause.pause()
    waiter = asyncio.create_task(routing_pause.wait_until_resumed())
    await _wait_for_waiters(1)

    waiter.cancel()
    with pytest.raises(asyncio.CancelledError):
        await waiter

    assert routing_pause.get_waiter_count() == 0


@pytest.mark.asyncio
async def test_pause_again_before_waiter_runs_keeps_it_blocked() -> None:
    routing_pause.pause()
    waiter = asyncio.create_task(routing_pause.wait_until_resumed())
    await _wait_for_waiters(1)

    routing_pause.resume()
    routing_pause.pause()
    await _wait_for_waiters(1)
    assert not waiter.done()

    routing_pause.resume()
    await asyncio.wait_for(waiter, timeout=1)
