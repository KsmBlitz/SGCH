-- Tenencia: organización → comunidad → unidad, accesos y auditoría (sección 10).
-- Todas las tablas nacen con RLS. La escritura de estas tablas la hace la API (rol que omite RLS).

create table public.organizaciones (
  id             uuid primary key default gen_random_uuid(),
  nombre         text not null check (length(trim(nombre)) > 0),
  plan           text not null default 'prueba' check (length(trim(plan)) > 0),
  prueba_hasta   date,
  creado_en      timestamptz not null default now()
);

create table public.miembros_organizacion (
  id               uuid primary key default gen_random_uuid(),
  organizacion_id  uuid not null references public.organizaciones (id),
  usuario_id       uuid not null references auth.users (id),
  rol              text not null check (rol in ('owner', 'staff')),
  creado_en        timestamptz not null default now(),
  unique (organizacion_id, usuario_id)
);

create index miembros_organizacion_usuario_idx on public.miembros_organizacion (usuario_id);

create table public.comunidades (
  id                  uuid primary key default gen_random_uuid(),
  organizacion_id     uuid not null references public.organizaciones (id),
  nombre              text not null check (length(trim(nombre)) > 0),
  -- RUT normalizado: sin puntos, con guion y dígito verificador en mayúscula.
  rut                 text check (rut ~ '^[0-9]{7,8}-[0-9K]$'),
  direccion           text,
  comuna              text,
  -- Recargo del fondo de reserva sobre el gasto ordinario; mínimo 5 %.
  -- Ley 21.442, art. 3 (recargo mínimo) [verificar]
  pct_reserva         numeric(9, 8) not null default 0.05 check (pct_reserva >= 0.05 and pct_reserva <= 1),
  -- Tasa de interés por mora. El tope legal lo valida la API [verificar tope].
  tasa_interes_mora   numeric(9, 8) not null default 0 check (tasa_interes_mora >= 0 and tasa_interes_mora <= 1),
  creado_en           timestamptz not null default now(),
  -- Permiten que las tablas hijas referencien (comunidad, organización) y no puedan mezclar clientes.
  unique (id, organizacion_id),
  unique (organizacion_id, rut)
);

create index comunidades_organizacion_idx on public.comunidades (organizacion_id);

create table public.unidades (
  id               uuid primary key default gen_random_uuid(),
  organizacion_id  uuid not null,
  comunidad_id     uuid not null,
  codigo           text not null check (length(trim(codigo)) > 0),
  tipo             text not null default 'departamento'
                   check (tipo in ('departamento', 'casa', 'local', 'estacionamiento', 'bodega')),
  -- Alícuota de la unidad. Las de una comunidad deben sumar exactamente 1 para poder cerrar.
  prorrateo        numeric(9, 8) not null check (prorrateo >= 0 and prorrateo <= 1),
  activa           boolean not null default true,
  creado_en        timestamptz not null default now(),
  foreign key (comunidad_id, organizacion_id) references public.comunidades (id, organizacion_id),
  unique (comunidad_id, codigo),
  unique (id, comunidad_id)
);

create table public.accesos_comunidad (
  id               uuid primary key default gen_random_uuid(),
  organizacion_id  uuid not null,
  comunidad_id     uuid not null,
  usuario_id       uuid not null references auth.users (id),
  rol              text not null check (rol in ('comite', 'residente')),
  unidad_id        uuid,
  creado_en        timestamptz not null default now(),
  foreign key (comunidad_id, organizacion_id) references public.comunidades (id, organizacion_id),
  foreign key (unidad_id, comunidad_id) references public.unidades (id, comunidad_id),
  -- El residente siempre queda atado a una unidad; el comité ve toda la comunidad.
  check ((rol = 'residente') = (unidad_id is not null)),
  unique nulls not distinct (usuario_id, comunidad_id, rol, unidad_id)
);

create index accesos_comunidad_usuario_idx on public.accesos_comunidad (usuario_id);

-- Registro inmutable de cambios con efecto económico.
create table public.auditoria (
  id               bigint generated always as identity primary key,
  organizacion_id  uuid not null references public.organizaciones (id),
  comunidad_id     uuid references public.comunidades (id),
  tabla            text not null,
  registro_id      uuid not null,
  accion           text not null check (accion in ('insert', 'update', 'delete')),
  usuario_id       uuid,
  anterior         jsonb,
  nuevo            jsonb,
  creado_en        timestamptz not null default now()
);

create index auditoria_organizacion_idx on public.auditoria (organizacion_id, creado_en);
create index auditoria_registro_idx on public.auditoria (tabla, registro_id);

-- ---------------------------------------------------------------------------
-- Funciones auxiliares de RLS (security definer: leen las tablas de acceso sin recursión)
-- ---------------------------------------------------------------------------

create function public.es_miembro_org(p_organizacion_id uuid)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select exists (
    select 1 from public.miembros_organizacion m
    where m.organizacion_id = p_organizacion_id and m.usuario_id = auth.uid()
  );
$$;

create function public.tiene_acceso_comunidad(p_comunidad_id uuid, p_roles text[])
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select exists (
    select 1 from public.accesos_comunidad a
    where a.comunidad_id = p_comunidad_id and a.usuario_id = auth.uid() and a.rol = any (p_roles)
  );
$$;

create function public.es_residente_unidad(p_unidad_id uuid)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select exists (
    select 1 from public.accesos_comunidad a
    where a.unidad_id = p_unidad_id and a.usuario_id = auth.uid() and a.rol = 'residente'
  );
$$;

-- Los prorrateos de una comunidad suman exactamente 1 (regla de la sección 8).
create function public.prorrateos_suman_uno(p_comunidad_id uuid)
returns boolean
language sql
stable
set search_path = ''
as $$
  select coalesce(sum(u.prorrateo), 0) = 1
  from public.unidades u
  where u.comunidad_id = p_comunidad_id;
$$;

-- Auditoría: copia la fila anterior y la nueva. Corre con los permisos del dueño para escribir
-- aunque quien cambia la fila no tenga acceso a `auditoria`.
create function public.registrar_auditoria()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_nuevo     jsonb := case when tg_op = 'DELETE' then null else to_jsonb(new) end;
  v_anterior  jsonb := case when tg_op = 'INSERT' then null else to_jsonb(old) end;
  v_fila      jsonb := coalesce(v_nuevo, v_anterior);
begin
  insert into public.auditoria
    (organizacion_id, comunidad_id, tabla, registro_id, accion, usuario_id, anterior, nuevo)
  values (
    (v_fila ->> 'organizacion_id')::uuid,
    case when tg_table_name = 'comunidades' then (v_fila ->> 'id')::uuid
         else (v_fila ->> 'comunidad_id')::uuid end,
    tg_table_name,
    (v_fila ->> 'id')::uuid,
    lower(tg_op),
    public.usuario_actual(),
    v_anterior,
    v_nuevo
  );
  return null;
end;
$$;

create function public.impedir_modificar_auditoria()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  raise exception 'La auditoría es de solo inserción.' using errcode = 'restrict_violation';
end;
$$;

grant execute on function
  public.es_miembro_org(uuid),
  public.tiene_acceso_comunidad(uuid, text[]),
  public.es_residente_unidad(uuid),
  public.prorrateos_suman_uno(uuid)
to authenticated, service_role;

-- ---------------------------------------------------------------------------
-- Triggers
-- ---------------------------------------------------------------------------

create trigger auditoria_sin_update_delete
  before update or delete on public.auditoria
  for each row execute function public.impedir_modificar_auditoria();

create trigger auditoria_sin_truncate
  before truncate on public.auditoria
  for each statement execute function public.impedir_modificar_auditoria();

create trigger organizaciones_sin_delete
  before delete on public.organizaciones
  for each row execute function public.impedir_borrado();

create trigger comunidades_sin_delete
  before delete on public.comunidades
  for each row execute function public.impedir_borrado();

create trigger unidades_sin_delete
  before delete on public.unidades
  for each row execute function public.impedir_borrado();

create trigger comunidades_auditoria
  after insert or update on public.comunidades
  for each row execute function public.registrar_auditoria();

create trigger unidades_auditoria
  after insert or update on public.unidades
  for each row execute function public.registrar_auditoria();

-- ---------------------------------------------------------------------------
-- RLS: lectura por rol; toda escritura pasa por la API.
-- ---------------------------------------------------------------------------

alter table public.organizaciones enable row level security;
alter table public.miembros_organizacion enable row level security;
alter table public.comunidades enable row level security;
alter table public.unidades enable row level security;
alter table public.accesos_comunidad enable row level security;
alter table public.auditoria enable row level security;

grant select on
  public.organizaciones, public.miembros_organizacion, public.comunidades,
  public.unidades, public.accesos_comunidad, public.auditoria
to authenticated;

create policy "organizaciones: equipo lee" on public.organizaciones
  for select to authenticated
  using (public.es_miembro_org(id));

create policy "miembros_organizacion: equipo lee" on public.miembros_organizacion
  for select to authenticated
  using (public.es_miembro_org(organizacion_id));

create policy "comunidades: equipo lee" on public.comunidades
  for select to authenticated
  using (public.es_miembro_org(organizacion_id));

create policy "comunidades: comite y residentes leen la suya" on public.comunidades
  for select to authenticated
  using (public.tiene_acceso_comunidad(id, array['comite', 'residente']));

create policy "unidades: equipo lee" on public.unidades
  for select to authenticated
  using (public.es_miembro_org(organizacion_id));

create policy "unidades: comite lee" on public.unidades
  for select to authenticated
  using (public.tiene_acceso_comunidad(comunidad_id, array['comite']));

create policy "unidades: residente lee las suyas" on public.unidades
  for select to authenticated
  using (public.es_residente_unidad(id));

create policy "accesos_comunidad: equipo lee" on public.accesos_comunidad
  for select to authenticated
  using (public.es_miembro_org(organizacion_id));

create policy "accesos_comunidad: cada usuario lee los suyos" on public.accesos_comunidad
  for select to authenticated
  using (usuario_id = auth.uid());

create policy "auditoria: equipo lee" on public.auditoria
  for select to authenticated
  using (public.es_miembro_org(organizacion_id));
