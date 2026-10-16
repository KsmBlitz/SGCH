# ADR 0005: Supabase CLI como única fuente de verdad del esquema; SQL explícito desde la API

- Estado: aceptada
- Fecha: 2026-10-15
- Origen: sección 9 del documento maestro

## Decisión

Supabase CLI como única fuente de verdad del esquema; SQL explícito desde la API.

## Motivo

Evita dos definiciones del esquema y versiona también RLS.

## Alternativa descartada

Alembic con ORM.
