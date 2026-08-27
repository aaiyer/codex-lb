from __future__ import annotations

from starlette.types import ASGIApp, Receive, Scope, Send

from app.core import routing_pause
from app.core.resilience.overload import is_proxy_path


class RoutingPauseMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] in {"http", "websocket"} and is_proxy_path(scope.get("path", "")):
            await routing_pause.wait_until_resumed()
        await self.app(scope, receive, send)
