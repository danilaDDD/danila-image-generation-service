import os

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response
        except Exception as e:
            if os.environ.get("ENV", "dev") != "test":
                logger = request.app.state.logger
                await logger.error(f"Unhandled exception: {e}", exc_info=True)
            raise e