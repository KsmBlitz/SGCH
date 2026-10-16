---
name: nueva-migracion
description: Crea una migración de Supabase para SGCH (tabla, columna, política RLS, función o trigger) con RLS, auditoría y pruebas pgTAP de aislamiento entre organizaciones. Úsala para cualquier cambio de esquema en supabase/.
argument-hint: "[descripción del cambio]"
---

# Nueva migración

Cambio pedido: $ARGUMENTS

## Pasos

1. Lee la sección 10 del documento maestro y `.claude/rules/supabase.md`. Revisa las migraciones
   existentes en `supabase/migrations/` para no duplicar nada.
2. Crea el archivo con `supabase migration new <nombre_snake_case>`. Nunca edites una migración ya
   aplicada.
3. Escribe el SQL a partir de [plantilla.sql](plantilla.sql). En cada tabla nueva:
   - `organizacion_id` (o una FK a una tabla que lo tenga) y una FK a `comunidades` si corresponde.
   - Tipos: `integer` para CLP, `numeric(9,8)` para prorrateos, `uuid` como PK, `timestamptz`.
   - Checks y uniques en la base, no solo en la API.
   - Si tiene efecto económico: columnas de anulación y trigger de auditoría.
   - `enable row level security` y políticas para el equipo, el comité y el residente.
4. Agrega pruebas pgTAP en `supabase/tests/database/<tabla>_test.sql` que cubran:
   - Un usuario de la organización A no lee, no inserta, no actualiza y no borra filas de la B.
   - El comité lee pero no escribe dinero.
   - El residente solo ve las filas de sus unidades.
5. Ejecuta `supabase db reset` y luego `supabase test db`. Los dos deben quedar en verde.
6. Si existe `apps/web`, regenera los tipos (`make types`).
7. Si agregaste datos al seed, que sean ficticios.

## Al terminar

Resume la tabla o el cambio, las políticas por rol y las pruebas agregadas, y señala cualquier
diferencia con la sección 10 del documento maestro.
