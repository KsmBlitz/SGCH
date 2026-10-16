---
paths:
  - "supabase/**"
---

# Reglas para `supabase/`

- Una migración por cambio, creada con `supabase migration new <nombre_en_snake_case>`. Nunca
  edites una migración ya aplicada: crea una nueva. Usa la skill `/nueva-migracion`.
- Tipos: montos `integer` (CLP), prorrateos `numeric(9,8)`, PK `uuid default gen_random_uuid()`,
  fechas de negocio `date`, marcas de tiempo `timestamptz`.
- Las tablas con efecto económico llevan `anulado_en timestamptz`, `anulado_por uuid` y
  `motivo text`, con un check que exige `motivo` cuando `anulado_en` no es nulo.
- `alter table ... enable row level security` en la misma migración que crea la tabla, con
  políticas basadas en `es_miembro_org(org_id)` y `tiene_acceso_comunidad(comunidad_id, roles[])`.
- Comité: lectura de su comunidad, sin escritura de dinero. Residente: solo filas de sus unidades.
- `auditoria`: solo inserción. Además de omitir las políticas de update y delete, agrega un
  trigger que rechace UPDATE y DELETE, porque el rol de la API omite RLS.
- Cada tabla nueva suma casos a `supabase/tests/database/` (pgTAP): la organización A no lee ni
  escribe nada de la B, y el residente solo ve sus unidades.
- Después de migrar: `supabase db reset` y `supabase test db` en verde, luego regenera los tipos.
- `seed.sql` solo contiene datos ficticios; nunca datos reales de personas.
