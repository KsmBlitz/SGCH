# ADR 0014: Aislamiento por claves compuestas, privilegios mínimos y escritura de dinero solo por la API

- Estado: aceptada
- Fecha: 2026-10-16
- Origen: etapa 3 (esquema, RLS y pgTAP); secciones 8 y 10 del documento maestro

## Contexto

La sección 10 exige RLS en toda tabla y que ninguna organización lea ni escriba datos de otra.
La API se conecta con un rol que omite RLS, así que ni las políticas ni el filtro de la API
bastan por sí solos si una fila apunta a una comunidad de otro cliente por error.

## Decisión

1. **Claves foráneas compuestas.** Toda tabla de negocio lleva `organizacion_id` y referencia a
   `(comunidad_id, organizacion_id)` de `comunidades`; las referencias entre tablas incluyen la
   comunidad (`(unidad_id, comunidad_id)`, `(periodo_id, comunidad_id)`) y, en la cobranza, la
   unidad (`(cargo_id, unidad_id)`, `(pago_id, unidad_id)`). Una fila no puede mezclar clientes,
   comunidades ni unidades aunque quien escribe omita RLS.
2. **Privilegios mínimos.** `anon` no tiene privilegios sobre ninguna tabla ni función de
   `public`. `authenticated` solo tiene `SELECT` en tablas con efecto económico y en tenencia;
   solo `personas`, `unidad_personas`, `proveedores` y `documentos` admiten escritura desde la web
   (con RLS). La escritura de dinero es exclusiva de la API.
3. **Visibilidad por rol.**
   - Equipo: toda su organización.
   - Comité: su comunidad completa, sin escritura. No ve personas ni la cartola bancaria
     (minimización, sección 15).
   - Residente: solo filas de sus unidades; los cargos solo una vez emitido el período; no ve
     gastos, fondo ni rendiciones.
4. **Reglas de integridad en la base**, además de la API: períodos solo avanzan
   abierto → cerrado → emitido; gastos y cargos solo nacen en períodos abiertos; los cargos no se
   editan ni se anulan una vez cerrado el período (se corrige con `ajuste`); no se puede cerrar
   si los prorrateos de la comunidad o de un grupo usado por un extraordinario no suman 1; un
   cargo vigente por unidad y concepto (cerrar dos veces no duplica); la suma aplicada no supera
   el pago ni el cargo; anular un pago anula sus aplicaciones; el fondo de reserva no queda con
   saldo negativo.
5. **Auditoría.** Triggers `registrar_auditoria` en las tablas con efecto económico; la API
   declara el usuario con `set_config('app.usuario_id', ..., true)` por transacción. La tabla
   rechaza UPDATE, DELETE y TRUNCATE incluso para el rol de la API.

## Motivo

Aplica en la base las reglas no negociables 3, 4 y 5 de `CLAUDE.md`: el filtro por organización
de la API deja de ser la única barrera contra referencias cruzadas, y un error de programación
en la web o en la API no puede alterar un período cerrado ni borrar dinero.

## Alternativa descartada

Confiar solo en `organizacion_id` con políticas RLS y filtros en la API: no impide que una fila
referencie la comunidad de otro cliente cuando la escribe el rol que omite RLS.

## Consecuencias

- Las FK compuestas obligan a que cada tabla padre tenga `unique (id, comunidad_id)` (o con
  organización); el costo es un índice adicional por tabla.
- La API debe declarar `app.usuario_id` en cada transacción de escritura para que la auditoría
  registre al usuario.
- Los parámetros pendientes de validación legal (tope de interés, orden de imputación, destino
  de intereses y multas, art. 39) siguen en la API; la base no los fija.
- Idempotencia de operaciones con `Idempotency-Key` queda para la etapa 4.
