---
paths:
  - "apps/web/**"
---

# Reglas para `apps/web`

- La web no calcula montos: todo monto viene de la API (`lib/api.ts`). Las lecturas simples pueden
  ir directo a Supabase protegidas por RLS.
- La clave `service_role` jamás llega al navegador ni a una variable `NEXT_PUBLIC_*`.
- Administrador: escritorio primero (mínimo 1366x768, objetivo 1920x1080), tablas densas,
  acciones en lote, atajos de teclado y previsualización antes de cerrar o emitir.
- Residente: móvil primero, lenguaje sin jerga contable y objetivos táctiles de 44 px.
- Formatos: montos `$1.234.567`, fechas `dd-mm-aaaa`, zona `America/Santiago`, español de Chile.
- Accesibilidad: contraste AA, etiquetas en todos los campos y navegación completa con teclado.
- `types/database.ts` es generado por Supabase CLI; no se edita a mano.
