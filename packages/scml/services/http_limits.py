"""Enforce a body limit before JSON parsing, including chunked requests."""

from starlette.responses import JSONResponse

from scml.services.ingestion import MAX_BYTES


class BoundedBodyMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["method"] not in ("POST", "PUT", "PATCH"):
            return await self.app(scope, receive, send)
        chunks = []
        size = 0
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            chunk = message.get("body", b"")
            size += len(chunk)
            if size > MAX_BYTES:
                response = JSONResponse(
                    status_code=413,
                    content={
                        "error": {
                            "code": "file_too_large",
                            "message": "Request exceeds 16 MiB",
                            "trace_id": scope.get("state", {}).get("trace_id", "unknown"),
                            "details": [],
                        }
                    },
                )
                return await response(scope, receive, send)
            chunks.append(chunk)
            if not message.get("more_body", False):
                break
        consumed = False

        async def replay():
            nonlocal consumed
            if not consumed:
                consumed = True
                return {"type": "http.request", "body": b"".join(chunks), "more_body": False}
            return await receive()

        return await self.app(scope, replay, send)
