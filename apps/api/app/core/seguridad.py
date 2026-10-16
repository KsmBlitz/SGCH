"""Verificación del JWT de Supabase (sección 11)."""

import asyncio
from functools import lru_cache
from uuid import UUID

import jwt
from jwt import PyJWKClient

from app.core.config import Configuracion
from app.core.errores import ErrorApi

_ALGORITMOS_ASIMETRICOS = ["ES256", "RS256"]


@lru_cache(maxsize=4)
def _cliente_jwks(url: str) -> PyJWKClient:
    return PyJWKClient(url, cache_keys=True)


def _no_autenticado() -> ErrorApi:
    return ErrorApi(401, "no_autenticado", "Token inválido o ausente.")


async def usuario_desde_token(token: str, config: Configuracion) -> UUID:
    """Devuelve el `sub` del token si la firma, el vencimiento y la audiencia son válidos."""
    try:
        alg = jwt.get_unverified_header(token).get("alg")
        if alg == "HS256" and config.jwt_secret:
            claims = jwt.decode(
                token, config.jwt_secret, algorithms=["HS256"], audience=config.jwt_audience
            )
        elif alg in _ALGORITMOS_ASIMETRICOS and config.jwks_url:
            clave = await asyncio.to_thread(
                _cliente_jwks(config.jwks_url).get_signing_key_from_jwt, token
            )
            claims = jwt.decode(
                token, clave.key, algorithms=_ALGORITMOS_ASIMETRICOS, audience=config.jwt_audience
            )
        else:
            raise _no_autenticado()
        if claims.get("role") != "authenticated":
            raise _no_autenticado()
        return UUID(str(claims["sub"]))
    except (jwt.PyJWTError, ValueError, KeyError) as exc:
        raise _no_autenticado() from exc
