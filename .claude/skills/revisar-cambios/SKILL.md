---
name: revisar-cambios
description: Revisa los cambios sin commitear de SGCH contra las reglas no negociables del proyecto (dinero en enteros, RLS y aislamiento por organización, anulación en vez de borrado, datos personales en logs, migraciones, puntos [verificar]). Úsala antes de un commit o PR, o cuando el usuario pida revisar cambios.
disable-model-invocation: true
---

# Revisión de cambios contra las reglas de SGCH

## Estado

!`git status --short`

## Diferencias (sin preparar y preparadas)

!`git diff --stat; git diff --cached --stat; git diff; git diff --cached`

## Cómo revisar

Los archivos nuevos sin seguimiento no aparecen en el diff: léelos directamente.

Recorre cada punto y reporta solo los hallazgos reales, con `ruta:línea`:

1. **Dinero:** ¿hay `float`, `round()` o `/` sobre montos? ¿Algún reparto que no use
   `prorrateo.repartir`? ¿Algún `Decimal(float)`?
2. **Invariantes:** ¿cada regla nueva tiene un caso tabulado y una propiedad Hypothesis?
3. **Anulación:** ¿hay `DELETE` o `UPDATE` destructivo sobre tablas con efecto económico?
   ¿Algún período cerrado se modifica en vez de ajustarse?
4. **Multi-tenencia:** ¿toda consulta de la API filtra por `organizacion_id`? ¿Toda tabla nueva
   tiene RLS y prueba pgTAP de aislamiento?
5. **Datos personales:** ¿hay RUT, nombre, correo o teléfono en logs, excepciones o mensajes?
6. **Esquema:** ¿hay cambios fuera de `supabase/migrations/`, o se editó una migración existente?
7. **Legal:** ¿hay reglas legales nuevas sin artículo o sin **[verificar]**?
8. **Secretos:** ¿hay claves en el código, o `service_role` en la web?
9. **Documentación:** ¿alguna decisión nueva sin ADR? ¿`CLAUDE.md` quedó desactualizado?

Luego ejecuta `make check` e informa el resultado.

## Formato del informe

Lista ordenada por severidad: **bloqueante**, **importante**, **sugerencia**. Si no hay
hallazgos, dilo en una línea. No apliques cambios sin que el usuario lo pida.
