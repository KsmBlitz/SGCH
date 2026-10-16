# ADR 0015: API con SQL explícito, idempotencia en la base y organización desde el JWT

- Estado: aceptada
- Fecha: 2026-10-16
- Origen: etapa 4; secciones 10 y 11 del documento maestro; complementa el ADR 0005

## Contexto

La API se conecta con un rol que omite RLS y es la única que escribe dinero. Necesita una forma
de acceder a la base que no duplique el esquema, de resolver la organización sin confiar en el
cliente y de que un reintento no repita un cierre o un pago.

## Decisión

1. **Acceso a datos:** SQLAlchemy Core asíncrono con `text()` y psycopg 3, sin ORM (ADR 0005). Una
   transacción por solicitud; `app.usuario_id` se declara con `set_config(..., true)`.
2. **Organización y rol:** salen de `miembros_organizacion` a partir del `sub` del JWT verificado
   (ES256/RS256 por JWKS, o HS256 con secreto). Un usuario en varias organizaciones indica cuál
   con `X-Organizacion-Id`, y la pertenencia siempre se verifica. Comité y residentes no usan los
   endpoints de administración. Una comunidad, unidad, pago o gasto de otra organización responde
   404, no 403, para no revelar su existencia.
3. **Idempotencia:** tabla `idempotencia` (clave única por organización) escrita en la misma
   transacción que la operación, con la huella de la solicitud y la respuesta. Un reintento
   devuelve la respuesta guardada con `Idempotent-Replayed: true`; la misma clave con otro
   contenido es 409; si la operación falla, la transacción se revierte y la clave queda libre.
   `Idempotency-Key` es obligatoria en gastos, cierre, pagos y anulaciones.
4. **Cierre:** una transacción que bloquea el período, calcula con `services.cierre`, inserta los
   cargos, cierra el período (la base valida que los prorrateos sumen 1) y aplica los saldos a
   favor existentes. El vencimiento de los cargos llega en la solicitud.
5. **Pagos:** se imputan con `services.cobranza.aplicar_pago` sobre los cargos de períodos
   cerrados o emitidos; el excedente queda como saldo a favor (pago con remanente sin aplicar) y se
   usa en el siguiente cierre.

## Motivo

Mantiene una sola definición del esquema, hace que el aislamiento dependa de una dependencia
central y de la base, y evita duplicar cargos o pagos ante reintentos de red.

## Alternativa descartada

ORM completo (duplica el esquema) e idempotencia en memoria o en Redis (se pierde la atomicidad
con la operación).

## Consecuencias

- Pendiente por **[verificar]** con abogado: tope legal de la tasa de interés, orden de
  imputación y destino de intereses y multas; la API usa los valores provisionales del motor.
- Un ajuste negativo (crédito) todavía no se compensa automáticamente contra deuda; la API no
  expone la creación de ajustes en esta etapa.
- Las filas de `idempotencia` necesitan limpieza periódica (tarea programada, etapa 7).
- La emisión (PDF y correo) queda para la etapa 6: hasta entonces los períodos quedan `cerrado`.
