-- Plantilla de referencia para una tabla de negocio de SGCH. Reemplaza <tabla> y ajusta las columnas.
-- Supone que ya existen es_miembro_org(uuid), tiene_acceso_comunidad(uuid, text[]) y la tabla auditoria.

create table public.<tabla> (
  id               uuid primary key default gen_random_uuid(),
  organizacion_id  uuid not null references public.organizaciones (id),
  comunidad_id     uuid not null references public.comunidades (id),
  -- columnas de negocio
  monto_clp        integer not null check (monto_clp >= 0),
  -- anulación (solo tablas con efecto económico)
  anulado_en       timestamptz,
  anulado_por      uuid references auth.users (id),
  motivo           text,
  creado_en        timestamptz not null default now(),
  creado_por       uuid references auth.users (id),
  constraint <tabla>_anulacion_con_motivo
    check (anulado_en is null or (anulado_por is not null and coalesce(length(trim(motivo)), 0) > 0))
);

create index <tabla>_comunidad_idx on public.<tabla> (comunidad_id);

alter table public.<tabla> enable row level security;

-- Equipo del administrador: todo lo de su organización.
create policy "<tabla>: equipo lee" on public.<tabla>
  for select to authenticated
  using (public.es_miembro_org(organizacion_id));

-- Comité: lectura de su comunidad, sin escritura de dinero.
create policy "<tabla>: comite lee" on public.<tabla>
  for select to authenticated
  using (public.tiene_acceso_comunidad(comunidad_id, array['comite']));

-- La escritura de dinero la hace solo la API (rol que omite RLS), así que no hay políticas
-- de insert, update ni delete para authenticated. Agrégalas solo para tablas sin efecto económico.

-- Auditoría de cambios con efecto económico.
create trigger <tabla>_auditoria
  after insert or update on public.<tabla>
  for each row execute function public.registrar_auditoria();

-- Bloquea el borrado físico de filas con efecto económico (incluso para el rol de la API).
create trigger <tabla>_sin_delete
  before delete on public.<tabla>
  for each row execute function public.impedir_borrado();
