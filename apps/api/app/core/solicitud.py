"""`X-Request-ID` en cada respuesta y en los logs (sección 11)."""

import logging
import uuid
from collections.abc import Awaitable, Callable
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

request_id_actual: ContextVar[str] = ContextVar("request_id", default="-")


class FiltroRequestId(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_actual.get()
        return True


def configurar_logs() -> None:
    manejador = logging.StreamHandler()
    manejador.addFilter(FiltroRequestId())
    manejador.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s request_id=%(request_id)s %(message)s")
    )
    raiz = logging.getLogger("sgch")
    raiz.handlers = [manejador]
    raiz.setLevel(logging.INFO)


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        recibido = request.headers.get("x-request-id", "")
        # Solo se acepta un identificador corto y simple; si no, se genera uno.
        rid = (
            recibido
            if 0 < len(recibido) <= 64 and recibido.isascii() and recibido.isprintable()
            else str(uuid.uuid4())
        )
        token = request_id_actual.set(rid)
        try:
            respuesta = await call_next(request)
        finally:
            request_id_actual.reset(token)
        respuesta.headers["X-Request-ID"] = rid
        return respuesta
