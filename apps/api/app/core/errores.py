"""Errores de la API con el formato único de la sección 11.

`{"error": {"code", "message", "details"}}`. Los mensajes y detalles nunca incluyen datos
personales (regla 8): los errores de validación omiten el valor recibido.
"""

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import DBAPIError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.services.cierre import CierreInvalidoError
from app.services.intereses import TasaInvalidaError
from app.services.prorrateo import ProrrateoInvalidoError

log = logging.getLogger("sgch.api")


class ErrorApi(Exception):
    def __init__(
        self, status: int, code: str, message: str, details: dict[str, Any] | None = None
    ) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.details = details or {}


def respuesta_error(
    status: int, code: str, message: str, details: dict[str, Any] | None = None
) -> JSONResponse:
    cuerpo = {"error": {"code": code, "message": message, "details": details or {}}}
    return JSONResponse(status_code=status, content=cuerpo)


# SQLSTATE que levantan las reglas de la base (migraciones de la etapa 3).
_ESTADOS_BD: dict[str, tuple[int, str]] = {
    "23001": (409, "regla_de_integridad"),  # restrict_violation: período cerrado, sin borrado...
    "23505": (409, "duplicado"),
    "23514": (422, "regla_de_negocio"),  # check_violation, incluido el cierre sin prorrateos en 1
    "23503": (422, "referencia_invalida"),
}


def registrar_manejadores(app: FastAPI) -> None:
    @app.exception_handler(ErrorApi)
    async def _error_api(_: Request, exc: ErrorApi) -> JSONResponse:
        return respuesta_error(exc.status, exc.code, exc.message, exc.details)

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        codigos = {401: "no_autenticado", 403: "prohibido", 404: "no_encontrado"}
        return respuesta_error(
            exc.status_code, codigos.get(exc.status_code, "error_http"), str(exc.detail)
        )

    @app.exception_handler(RequestValidationError)
    async def _validacion(_: Request, exc: RequestValidationError) -> JSONResponse:
        # Solo ubicación y tipo de error: el valor recibido podría ser un dato personal.
        campos = [
            {"campo": ".".join(str(p) for p in e["loc"]), "tipo": e["type"]} for e in exc.errors()
        ]
        return respuesta_error(422, "validacion", "La solicitud no es válida.", {"campos": campos})

    @app.exception_handler(CierreInvalidoError)
    @app.exception_handler(ProrrateoInvalidoError)
    @app.exception_handler(TasaInvalidaError)
    async def _dominio(_: Request, exc: ValueError) -> JSONResponse:
        return respuesta_error(422, "regla_de_negocio", str(exc))

    @app.exception_handler(DBAPIError)
    async def _bd(_: Request, exc: DBAPIError) -> JSONResponse:
        estado = getattr(exc.orig, "sqlstate", None)
        if estado in _ESTADOS_BD:
            status, code = _ESTADOS_BD[estado]
            diag = getattr(exc.orig, "diag", None)
            mensaje = (
                getattr(diag, "message_primary", None) or "La base de datos rechazó la operación."
            )
            return respuesta_error(status, code, mensaje)
        log.error("error_bd sqlstate=%s", estado)
        return respuesta_error(500, "error_interno", "Error interno del servidor.")

    @app.exception_handler(Exception)
    async def _inesperado(_: Request, exc: Exception) -> JSONResponse:
        log.error("error_inesperado tipo=%s", type(exc).__name__)
        return respuesta_error(500, "error_interno", "Error interno del servidor.")
