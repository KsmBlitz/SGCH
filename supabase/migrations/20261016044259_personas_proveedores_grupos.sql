-- Personas, relación con unidades, proveedores y grupos de prorrateo (sección 10).
-- Personas, vínculos y proveedores no tienen efecto económico: el equipo los edita desde la web
-- con RLS. Los grupos de prorrateo sí alteran montos, así que solo los escribe la API.

create table public.personas (
  id                uuid primary key default gen_random_uuid(),
  organizacion_id   uuid not null references public.organizaciones (id),
  nombre            text not null check (length(trim(nombre)) > 0),
  rut               text check (rut ~ '^[0-9]{7,8}-[0-9K]$'),
  correo            text,
  telefono          text,
  -- Ley 21.719: fecha en que la persona consintió el tratamiento de sus datos [validar con abogado].
  consentimiento_en timestamptz,
  creado_en         timestamptz not null default now(),
  unique (id, organizacion_id),
  unique (organizacion_id, rut)
);

create index personas_organizacion_idx on public.personas (organizacion_id);

create table public.unidad_personas (
  id               uuid primary key default gen_random_uuid(),
  organizacion_id  uuid not null,
  comunidad_id     uuid not null,
  unidad_id        uuid not null,
  persona_id       uuid not null,
  rol              text not null check (rol in ('propietario', 'residente')),
  desde            date not null,
  hasta            date,
  creado_en        timestamptz not null default now(),
  foreign key (comunidad_id, organizacion_id) references public.comunidades (id, organizacion_id),
  foreign key (unidad_id, comunidad_id) references public.unidades (id, comunidad_id),
  foreign key (persona_id, organizacion_id) references public.personas (id, organizacion_id),
  check (hasta is null or hasta >= desde),
  unique (unidad_id, persona_id, rol, desde)
);

create index unidad_personas_unidad_idx on public.unidad_personas (unidad_id);
create index unidad_personas_persona_idx on public.unidad_personas (persona_id);
create index unidad_personas_comunidad_idx on public.unidad_personas (comunidad_id);

create table public.proveedores (
  id               uuid primary key default gen_random_uuid(),
  organizacion_id  uuid not null,
  comunidad_id     uuid not null,
  nombre           text not null check (length(trim(nombre)) > 0),
  rut              text check (rut ~ '^[0-9]{7,8}-[0-9K]$'),
  giro             text,
  creado_en        timestamptz not null default now(),
  foreign key (comunidad_id, organizacion_id) references public.comunidades (id, organizacion_id),
  unique (id, comunidad_id),
  unique (comunidad_id, rut)
);

create index proveedores_comunidad_idx on public.proveedores (comunidad_id);

-- Prorrateos alternativos (por torre o por servicio) para gastos extraordinarios.
create table public.grupos_prorrateo (
  id               uuid primary key default gen_random_uuid(),
  organizacion_id  uuid not null,
  comunidad_id     uuid not null,
  nombre           text not null check (length(trim(nombre)) > 0),
  creado_en        timestamptz not null default now(),
  foreign key (comunidad_id, organizacion_id) references public.comunidades (id, organizacion_id),
  unique (id, comunidad_id),
  unique (comunidad_id, nombre)
);

create table public.grupo_prorrateo_unidades (
  id               uuid primary key default gen_random_uuid(),
  organizacion_id  uuid not null,
  comunidad_id     uuid not null,
  grupo_id         uuid not null,
  unidad_id        uuid not null,
  prorrateo        numeric(9, 8) not null check (prorrateo > 0 and prorrateo <= 1),
  foreign key (comunidad_id, organizacion_id) references public.comunidades (id, organizacion_id),
  foreign key (grupo_id, comunidad_id) references public.grupos_prorrateo (id, comunidad_id),
  foreign key (unidad_id, comunidad_id) references public.unidades (id, comunidad_id),
  unique (grupo_id, unidad_id)
);

create index grupo_prorrateo_unidades_comunidad_idx on public.grupo_prorrateo_unidades (comunidad_id);

-- Los prorrateos de un grupo suman exactamente 1 (sección 10). El cierre lo exige.
create function public.grupo_prorrateo_suma_uno(p_grupo_id uuid)
returns boolean
language sql
stable
set search_path = ''
as $$
  select coalesce(sum(g.prorrateo), 0) = 1
  from public.grupo_prorrateo_unidades g
  where g.grupo_id = p_grupo_id;
$$;

grant execute on function public.grupo_prorrateo_suma_uno(uuid) to authenticated, service_role;

-- Cambiar la membresía de un grupo altera cobros futuros: queda en la auditoría, incluso el borrado.
create trigger grupo_prorrateo_unidades_auditoria
  after insert or update or delete on public.grupo_prorrateo_unidades
  for each row execute function public.registrar_auditoria();

-- ---------------------------------------------------------------------------
-- RLS
-- ---------------------------------------------------------------------------

alter table public.personas enable row level security;
alter table public.unidad_personas enable row level security;
alter table public.proveedores enable row level security;
alter table public.grupos_prorrateo enable row level security;
alter table public.grupo_prorrateo_unidades enable row level security;

grant select, insert, update, delete on
  public.personas, public.unidad_personas, public.proveedores
to authenticated;
grant select on public.grupos_prorrateo, public.grupo_prorrateo_unidades to authenticated;

-- Personas: equipo con control total; el residente ve a las personas de su unidad.
create policy "personas: equipo lee" on public.personas
  for select to authenticated using (public.es_miembro_org(organizacion_id));
create policy "personas: equipo inserta" on public.personas
  for insert to authenticated with check (public.es_miembro_org(organizacion_id));
create policy "personas: equipo actualiza" on public.personas
  for update to authenticated
  using (public.es_miembro_org(organizacion_id))
  with check (public.es_miembro_org(organizacion_id));
create policy "personas: equipo borra" on public.personas
  for delete to authenticated using (public.es_miembro_org(organizacion_id));
create policy "personas: residente ve las de su unidad" on public.personas
  for select to authenticated
  using (exists (
    select 1 from public.unidad_personas up
    where up.persona_id = personas.id and public.es_residente_unidad(up.unidad_id)
  ));

create policy "unidad_personas: equipo lee" on public.unidad_personas
  for select to authenticated using (public.es_miembro_org(organizacion_id));
create policy "unidad_personas: equipo inserta" on public.unidad_personas
  for insert to authenticated with check (public.es_miembro_org(organizacion_id));
create policy "unidad_personas: equipo actualiza" on public.unidad_personas
  for update to authenticated
  using (public.es_miembro_org(organizacion_id))
  with check (public.es_miembro_org(organizacion_id));
create policy "unidad_personas: equipo borra" on public.unidad_personas
  for delete to authenticated using (public.es_miembro_org(organizacion_id));
create policy "unidad_personas: residente ve las de su unidad" on public.unidad_personas
  for select to authenticated using (public.es_residente_unidad(unidad_id));

create policy "proveedores: equipo lee" on public.proveedores
  for select to authenticated using (public.es_miembro_org(organizacion_id));
create policy "proveedores: equipo inserta" on public.proveedores
  for insert to authenticated with check (public.es_miembro_org(organizacion_id));
create policy "proveedores: equipo actualiza" on public.proveedores
  for update to authenticated
  using (public.es_miembro_org(organizacion_id))
  with check (public.es_miembro_org(organizacion_id));
create policy "proveedores: equipo borra" on public.proveedores
  for delete to authenticated using (public.es_miembro_org(organizacion_id));
create policy "proveedores: comite lee" on public.proveedores
  for select to authenticated
  using (public.tiene_acceso_comunidad(comunidad_id, array['comite']));

create policy "grupos_prorrateo: equipo lee" on public.grupos_prorrateo
  for select to authenticated using (public.es_miembro_org(organizacion_id));
create policy "grupos_prorrateo: comite lee" on public.grupos_prorrateo
  for select to authenticated
  using (public.tiene_acceso_comunidad(comunidad_id, array['comite']));

create policy "grupo_prorrateo_unidades: equipo lee" on public.grupo_prorrateo_unidades
  for select to authenticated using (public.es_miembro_org(organizacion_id));
create policy "grupo_prorrateo_unidades: comite lee" on public.grupo_prorrateo_unidades
  for select to authenticated
  using (public.tiene_acceso_comunidad(comunidad_id, array['comite']));
