-- Ciclo mensual: períodos, gastos y cargos (secciones 8 y 10; ADR 0007).
-- Todo lo que toca dinero lo escribe la API. La base refuerza las reglas que no pueden fallar:
-- períodos cerrados inmutables, prorrateos que suman 1 al cerrar y cierre idempotente.

create table public.periodos (
  id               uuid primary key default gen_random_uuid(),
  organizacion_id  uuid not null,
  comunidad_id     uuid not null,
  -- Primer día del mes contable (America/Santiago).
  mes              date not null check (mes = date_trunc('month', mes)::date),
  estado           text not null default 'abierto' check (estado in ('abierto', 'cerrado', 'emitido')),
  cerrado_en       timestamptz,
  cerrado_por      uuid references auth.users (id),
  emitido_en       timestamptz,
  creado_en        timestamptz not null default now(),
  foreign key (comunidad_id, organizacion_id) references public.comunidades (id, organizacion_id),
  unique (comunidad_id, mes),
  unique (id, comunidad_id),
  check ((estado = 'abierto') = (cerrado_en is null and cerrado_por is null)),
  check ((estado = 'emitido') = (emitido_en is not null))
);

create table public.gastos (
  id                   uuid primary key default gen_random_uuid(),
  organizacion_id      uuid not null,
  comunidad_id         uuid not null,
  periodo_id           uuid not null,
  tipo                 text not null check (tipo in ('ordinario', 'extraordinario')),
  -- Categorías de la sección 3 [verificar contra la Ley 21.442].
  categoria            text not null check (length(trim(categoria)) > 0),
  descripcion          text not null check (length(trim(descripcion)) > 0),
  monto_clp            integer not null check (monto_clp > 0),
  fecha                date not null,
  proveedor_id         uuid,
  -- Ruta en Storage; su ausencia solo genera una advertencia en la revisión del período.
  comprobante_path     text,
  -- Extraordinario prorrateado con un criterio distinto al de la comunidad (p. ej. una torre).
  grupo_prorrateo_id   uuid,
  -- Un extraordinario solo se prorratea una vez aprobado.
  aprobado_en          timestamptz,
  aprobado_por         uuid references auth.users (id),
  anulado_en           timestamptz,
  anulado_por          uuid references auth.users (id),
  motivo               text,
  creado_en            timestamptz not null default now(),
  creado_por           uuid references auth.users (id),
  foreign key (comunidad_id, organizacion_id) references public.comunidades (id, organizacion_id),
  foreign key (periodo_id, comunidad_id) references public.periodos (id, comunidad_id),
  foreign key (proveedor_id, comunidad_id) references public.proveedores (id, comunidad_id),
  foreign key (grupo_prorrateo_id, comunidad_id) references public.grupos_prorrateo (id, comunidad_id),
  unique (id, comunidad_id),
  check (tipo = 'extraordinario' or categoria in ('administracion', 'mantencion', 'reparacion', 'uso_consumo')),
  check (tipo = 'extraordinario' or (grupo_prorrateo_id is null and aprobado_en is null)),
  check ((aprobado_en is null) = (aprobado_por is null)),
  constraint gastos_anulacion_con_motivo
    check (anulado_en is null or (anulado_por is not null and coalesce(length(trim(motivo)), 0) > 0))
);

create index gastos_periodo_idx on public.gastos (periodo_id);
create index gastos_comunidad_idx on public.gastos (comunidad_id);

create table public.cargos (
  id               uuid primary key default gen_random_uuid(),
  organizacion_id  uuid not null,
  comunidad_id     uuid not null,
  periodo_id       uuid not null,
  unidad_id        uuid not null,
  concepto         text not null
                   check (concepto in ('gasto_comun', 'reserva', 'extraordinario', 'interes', 'multa', 'ajuste')),
  -- Un ajuste puede ser negativo (abono a favor); el resto es siempre positivo.
  monto_clp        integer not null check (monto_clp <> 0),
  vencimiento      date not null,
  -- Gasto extraordinario que originó el cargo.
  gasto_id         uuid,
  referencia       text,
  anulado_en       timestamptz,
  anulado_por      uuid references auth.users (id),
  motivo           text,
  creado_en        timestamptz not null default now(),
  creado_por       uuid references auth.users (id),
  foreign key (comunidad_id, organizacion_id) references public.comunidades (id, organizacion_id),
  foreign key (periodo_id, comunidad_id) references public.periodos (id, comunidad_id),
  foreign key (unidad_id, comunidad_id) references public.unidades (id, comunidad_id),
  foreign key (gasto_id, comunidad_id) references public.gastos (id, comunidad_id),
  unique (id, comunidad_id),
  unique (id, unidad_id),
  check (concepto = 'ajuste' or monto_clp > 0),
  check ((concepto = 'extraordinario') = (gasto_id is not null)),
  constraint cargos_anulacion_con_motivo
    check (anulado_en is null or (anulado_por is not null and coalesce(length(trim(motivo)), 0) > 0))
);

create index cargos_periodo_idx on public.cargos (periodo_id);
create index cargos_unidad_idx on public.cargos (unidad_id);
create index cargos_comunidad_idx on public.cargos (comunidad_id);

-- Cerrar dos veces un período no duplica cargos: un cargo vigente por unidad y concepto.
create unique index cargos_unico_por_concepto
  on public.cargos (periodo_id, unidad_id, concepto)
  where anulado_en is null and concepto in ('gasto_comun', 'reserva', 'interes');

create unique index cargos_unico_extraordinario
  on public.cargos (periodo_id, unidad_id, gasto_id)
  where anulado_en is null and concepto = 'extraordinario';

-- ---------------------------------------------------------------------------
-- Reglas de integridad
-- ---------------------------------------------------------------------------

-- Los períodos solo avanzan abierto → cerrado → emitido, y un período cerrado no se edita.
create function public.periodos_control()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  if new.organizacion_id <> old.organizacion_id
     or new.comunidad_id <> old.comunidad_id
     or new.mes <> old.mes then
    raise exception 'La comunidad y el mes de un período no se pueden cambiar.'
      using errcode = 'restrict_violation';
  end if;

  if old.estado <> 'abierto' and new.estado = old.estado and new is distinct from old then
    raise exception 'El período % ya está %; se corrige con un ajuste en el período siguiente.',
      old.mes, old.estado using errcode = 'restrict_violation';
  end if;

  if new.estado <> old.estado
     and not ((old.estado, new.estado) in (('abierto', 'cerrado'), ('cerrado', 'emitido'))) then
    raise exception 'Transición de período no permitida: % → %.', old.estado, new.estado
      using errcode = 'restrict_violation';
  end if;

  if old.estado = 'abierto' and new.estado = 'cerrado' then
    if not public.prorrateos_suman_uno(new.comunidad_id) then
      raise exception 'No se puede cerrar: los prorrateos de la comunidad no suman 1.'
        using errcode = 'check_violation';
    end if;
    if exists (
      select 1
      from public.gastos g
      where g.periodo_id = new.id
        and g.anulado_en is null
        and g.aprobado_en is not null
        and g.grupo_prorrateo_id is not null
        and not public.grupo_prorrateo_suma_uno(g.grupo_prorrateo_id)
    ) then
      raise exception 'No se puede cerrar: un grupo de prorrateo no suma 1.'
        using errcode = 'check_violation';
    end if;
  end if;
  return new;
end;
$$;

create trigger periodos_control
  before update on public.periodos
  for each row execute function public.periodos_control();

-- Gastos: solo se registran o editan mientras el período está abierto.
create function public.gastos_control()
returns trigger
language plpgsql
set search_path = ''
as $$
declare
  v_estado text;
begin
  if tg_op = 'UPDATE' and new.periodo_id <> old.periodo_id then
    raise exception 'Un gasto no cambia de período.' using errcode = 'restrict_violation';
  end if;

  select p.estado into v_estado from public.periodos p where p.id = new.periodo_id for share;
  if v_estado <> 'abierto' then
    raise exception 'El período está %; los gastos se congelaron en el cierre.', v_estado
      using errcode = 'restrict_violation';
  end if;
  if tg_op = 'UPDATE' and old.anulado_en is not null then
    raise exception 'El gasto ya está anulado y no se puede modificar.'
      using errcode = 'restrict_violation';
  end if;
  return new;
end;
$$;

create trigger gastos_control
  before insert or update on public.gastos
  for each row execute function public.gastos_control();

-- Cargos: nacen solo en períodos abiertos (el cierre los crea antes de cerrar) y no se editan.
-- Una vez cerrado el período tampoco se anulan: se corrigen con un cargo `ajuste` en el siguiente.
create function public.cargos_control()
returns trigger
language plpgsql
set search_path = ''
as $$
declare
  v_estado text;
begin
  select p.estado into v_estado from public.periodos p where p.id = new.periodo_id for share;
  if tg_op = 'INSERT' and v_estado <> 'abierto' then
    raise exception 'El período está %; no se agregan cargos, usa un ajuste en el período siguiente.',
      v_estado using errcode = 'restrict_violation';
  end if;
  if tg_op = 'UPDATE' and v_estado <> 'abierto' then
    raise exception 'El período está %; el cargo se corrige con un ajuste en el período siguiente.',
      v_estado using errcode = 'restrict_violation';
  end if;
  return new;
end;
$$;

create trigger cargos_control
  before insert or update on public.cargos
  for each row execute function public.cargos_control();

create trigger cargos_solo_anulacion
  before update on public.cargos
  for each row execute function public.impedir_edicion_salvo_anulacion();

create trigger periodos_sin_delete before delete on public.periodos
  for each row execute function public.impedir_borrado();
create trigger gastos_sin_delete before delete on public.gastos
  for each row execute function public.impedir_borrado();
create trigger cargos_sin_delete before delete on public.cargos
  for each row execute function public.impedir_borrado();

create trigger periodos_auditoria after insert or update on public.periodos
  for each row execute function public.registrar_auditoria();
create trigger gastos_auditoria after insert or update on public.gastos
  for each row execute function public.registrar_auditoria();
create trigger cargos_auditoria after insert or update on public.cargos
  for each row execute function public.registrar_auditoria();

-- ---------------------------------------------------------------------------
-- RLS: la escritura de dinero es solo de la API.
-- ---------------------------------------------------------------------------

alter table public.periodos enable row level security;
alter table public.gastos enable row level security;
alter table public.cargos enable row level security;

grant select on public.periodos, public.gastos, public.cargos to authenticated;

create policy "periodos: equipo lee" on public.periodos
  for select to authenticated using (public.es_miembro_org(organizacion_id));
create policy "periodos: comite y residentes leen" on public.periodos
  for select to authenticated
  using (public.tiene_acceso_comunidad(comunidad_id, array['comite', 'residente']));

create policy "gastos: equipo lee" on public.gastos
  for select to authenticated using (public.es_miembro_org(organizacion_id));
create policy "gastos: comite lee" on public.gastos
  for select to authenticated
  using (public.tiene_acceso_comunidad(comunidad_id, array['comite']));

create policy "cargos: equipo lee" on public.cargos
  for select to authenticated using (public.es_miembro_org(organizacion_id));
create policy "cargos: comite lee" on public.cargos
  for select to authenticated
  using (public.tiene_acceso_comunidad(comunidad_id, array['comite']));
-- El residente ve los cargos de sus unidades solo una vez emitido el período.
create policy "cargos: residente lee los emitidos de su unidad" on public.cargos
  for select to authenticated
  using (
    public.es_residente_unidad(unidad_id)
    and exists (
      select 1 from public.periodos p where p.id = cargos.periodo_id and p.estado = 'emitido'
    )
  );
