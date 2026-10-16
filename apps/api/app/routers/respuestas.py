from fastapi.responses import JSONResponse

from app.core.idempotencia import Respuesta


def responder(respuesta: Respuesta, repetida: bool) -> JSONResponse:
    cabeceras = {"Idempotent-Replayed": "true"} if repetida else {}
    return JSONResponse(status_code=respuesta.status, content=respuesta.cuerpo, headers=cabeceras)
