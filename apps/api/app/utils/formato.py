"""Formato de montos y fechas en español de Chile (sección 12 del documento maestro)."""

from datetime import date
from zoneinfo import ZoneInfo

ZONA_NEGOCIO = ZoneInfo("America/Santiago")


def formatear_clp(monto_clp: int) -> str:
    """1234567 -> "$1.234.567"; -1500 -> "-$1.500"."""
    if isinstance(monto_clp, bool) or not isinstance(monto_clp, int):
        raise TypeError("Los montos CLP son enteros.")
    signo = "-" if monto_clp < 0 else ""
    return f"{signo}${abs(monto_clp):,}".replace(",", ".")


def formatear_fecha(fecha: date) -> str:
    """dd-mm-aaaa."""
    return fecha.strftime("%d-%m-%Y")


def mes_desde_texto(texto: str) -> date:
    """ "2026-10" -> primer día del mes contable (2026-10-01)."""
    try:
        anio, mes = texto.split("-")
        if len(anio) != 4 or len(mes) != 2:
            raise ValueError
        return date(int(anio), int(mes), 1)
    except ValueError as exc:
        raise ValueError("El período debe tener el formato aaaa-mm.") from exc
