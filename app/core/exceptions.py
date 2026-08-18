from fastapi import Request, status
from fastapi.responses import JSONResponse


class PlatformException(Exception):
    def __init__(self, message: str, status_code: int = status.HTTP_400_BAD_REQUEST):
        self.message = message
        self.status_code = status_code


async def platform_exception_handler(
    request: Request, exc: PlatformException
) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})
