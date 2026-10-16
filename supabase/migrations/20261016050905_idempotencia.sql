-- Idempotencia de las operaciones de dinero de la API (sección 11: cabecera Idempotency-Key).
-- La API inserta la fila en la misma transacción que la operación y guarda la respuesta, de modo
-- que un reintento con la misma clave devuelve la respuesta original sin repetir el efecto.
-- Solo la API la usa: ningún rol de la web tiene privilegios sobre esta tabla.

create table public.idempotencia (
  id               uuid primary key default gen_random_uuid(),
  organizacion_id  uuid not null references public.organizaciones (id),
  clave            text not null check (length(clave) between 1 and 255),
  operacion        text not null check (length(operacion) > 0),
  -- Hash de la solicitud: la misma clave con otro contenido es un error del cliente.
  huella           text not null check (length(huella) > 0),
  codigo_http      integer,
  respuesta        jsonb,
  creado_en        timestamptz not null default now(),
  unique (organizacion_id, clave),
  check ((codigo_http is null) = (respuesta is null))
);

create index idempotencia_creado_idx on public.idempotencia (creado_en);

alter table public.idempotencia enable row level security;
-- Sin políticas ni privilegios para anon o authenticated: la lee y escribe solo la API.
