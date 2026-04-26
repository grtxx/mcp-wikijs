from starlette.responses import Response
from starlette.types import ASGIApp, Receive, Scope, Scope, Send
from configmanager import config as cfg


class TokenAuthMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app
        self._token = str(cfg.get("mcp_api_token"))

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] == "http":
            from urllib.parse import parse_qs
            query_string = scope.get("query_string", b"").decode()
            params = parse_qs(query_string)
            token = params.get("token", [None])[0]
            if token != self._token:
                response = Response("Unauthorized", status_code=401)
                await response(scope, receive, send)
                return
        await self.app(scope, receive, send)


def __init__():
    pass