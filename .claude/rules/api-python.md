---
paths:
  - "apps/api/**/*.py"
---

# Reglas para `apps/api`

- `app/services/` contiene funciones puras: sin I/O, sin BD, sin reloj (`date.today()` llega como
  parámetro `fecha_corte`). La persistencia, la auditoría y la idempotencia van en la capa de API.
- Los montos CLP son `int`; valida `isinstance(x, bool)` aparte, porque `True` es un `int`.
- Para tasas y prorrateos usa `Decimal` en la interfaz y `Fraction` en el cálculo. Nunca construyas
  un `Decimal` desde un `float`.
- Todo reparto entre unidades usa `prorrateo.repartir`. El orden de entrada desempata, así que
  ordena por código de unidad antes de llamar.
- Los errores de dominio heredan de `ValueError` con nombre `<Algo>InvalidoError` y mensaje en
  español, sin datos personales.
- Las constantes legales (`PCT_RESERVA_MINIMO`, `ORDEN_IMPUTACION`, `UMBRAL_CUOTAS_IMPAGAS`...) van
  en mayúsculas al inicio del módulo, con comentario de artículo y **[verificar]** si corresponde.
- Las pruebas nuevas de dinero usan `tests/comunidad_ficticia.py` o casos chicos verificables a
  mano, más una propiedad Hypothesis del invariante.
- Desde la etapa 4: errores HTTP con formato `{"error": {"code", "message", "details"}}`, prefijo
  `/api/v1`, `Idempotency-Key` en operaciones de dinero y `X-Request-ID` en logs.
