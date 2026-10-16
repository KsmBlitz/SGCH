-- Cobranza: pagos, aplicaciones de pago y movimientos de cartola (secciones 8 y 10).
-- Un pago nunca se borra ni se edita: se anula con motivo y la deuda se restituye porque el
-- saldo de un cargo se calcula con las aplicaciones vigentes.

create table public.pagos (
  id                uuid primary key default gen_random_uuid(),
  organizacion_id   uuid not null,
  comunidad_id      uuid not null,
  unidad_id         uuid not null,
  monto_clp         integer not null check (monto_clp > 0),
  fecha_pago        date not null,
  medio             text not null
                    check (medio in ('transferencia', 'efectivo', 'cheque', 'tarjeta', 'otro')),
  origen            text not null default 'manual' check (origen in ('manual', 'cartola', 'pasarela')),
  referencia        text,
  anulado_en        timestamptz,
  anulado_por       uuid references auth.users (id),
  motivo            text,
  creado_en         timestamptz not null default now(),
  creado_por        uuid references auth.users (id),
  foreign key (comunidad_id, organizacion_id) references public.comunidades (id, organizacion_id),
  foreign key (unidad_id, comunidad_id) references public.unidades (id, comunidad_id),
  unique (id, comunidad_id),
  unique (id, unidad_id),
  constraint pagos_anulacion_con_motivo
    check (anulado_en is null or (anulado_por is not null and coalesce(length(trim(motivo)), 0) > 0))
);

create index pagos_unidad_idx on public.pagos (unidad_id);
create index pagos_comunidad_idx on public.pagos (comunidad_id);

create table public.aplicaciones_pago (
  id                uuid primary key default gen_random_uuid(),
  organizacion_id   uuid not null,
  comunidad_id      uuid not null,
  unidad_id         uuid not null,
  pago_id           uuid not null,
  cargo_id          uuid not null,
  monto_clp         integer not null check (monto_clp > 0),
  anulado_en        timestamptz,
  anulado_por       uuid references auth.users (id),
  motivo            text,
  creado_en         timestamptz not null default now(),
  creado_por        uuid references auth.users (id),
  foreign key (comunidad_id, organizacion_id) references public.comunidades (id, organizacion_id),
  foreign key (unidad_id, comunidad_id) references public.unidades (id, comunidad_id),
  -- El pago y el cargo deben ser de la misma unidad que la aplicación.
  foreign key (pago_id, unidad_id) references public.pagos (id, unidad_id),
  foreign key (cargo_id, unidad_id) references public.cargos (id, unidad_id),
  constraint aplicaciones_pago_anulacion_con_motivo
    check (anulado_en is null or (anulado_por is not null and coalesce(length(trim(motivo)), 0) > 0))
);

create index aplicaciones_pago_pago_idx on public.aplicaciones_pago (pago_id);
create index aplicaciones_pago_cargo_idx on public.aplicaciones_pago (cargo_id);
create index aplicaciones_pago_unidad_idx on public.aplicaciones_pago (unidad_id);

-- Líneas importadas de la cartola del banco. El hash evita importar dos veces la misma línea.
create table public.movimientos_cartola (
  id                uuid primary key default gen_random_uuid(),
  organizacion_id   uuid not null,
  comunidad_id      uuid not null,
  fecha             date not null,
  descripcion       text not null,
  -- Positivo = abono a la cuenta; negativo = cargo.
  monto_clp         integer not null check (monto_clp <> 0),
  hash              text not null check (length(hash) > 0),
  estado            text not null default 'pendiente'
                    check (estado in ('pendiente', 'propuesto', 'conciliado', 'ignorado')),
  pago_id           uuid,
  gasto_id          uuid,
  creado_en         timestamptz not null default now(),
  foreign key (comunidad_id, organizacion_id) references public.comunidades (id, organizacion_id),
  foreign key (pago_id, comunidad_id) references public.pagos (id, comunidad_id),
  foreign key (gasto_id, comunidad_id) references public.gastos (id, comunidad_id),
  unique (comunidad_id, hash),
  check (pago_id is null or gasto_id is null),
  check ((estado in ('propuesto', 'conciliado')) = (pago_id is not null or gasto_id is not null))
);

create index movimientos_cartola_comunidad_idx on public.movimientos_cartola (comunidad_id, fecha);

-- Un pago se concilia con una sola línea de cartola.
create unique index movimientos_cartola_pago_unico
  on public.movimientos_cartola (pago_id)
  where pago_id is not null and estado in ('propuesto', 'conciliado');

-- ---------------------------------------------------------------------------
-- Reglas de integridad
-- ---------------------------------------------------------------------------

-- La suma aplicada no supera el pago ni el cargo, y no se aplica a cargos o pagos anulados.
create function public.aplicaciones_pago_control()
returns trigger
language plpgsql
set search_path = ''
as $$
declare
  v_pago   public.pagos%rowtype;
  v_cargo  public.cargos%rowtype;
  v_aplicado_pago   bigint;
  v_aplicado_cargo  bigint;
begin
  -- Bloquea el pago para que dos aplicaciones simultáneas no lo sobrepasen.
  select * into v_pago from public.pagos where id = new.pago_id for update;
  select * into v_cargo from public.cargos where id = new.cargo_id for update;

  if v_pago.unidad_id is distinct from new.unidad_id or v_cargo.unidad_id is distinct from new.unidad_id then
    raise exception 'El pago y el cargo deben pertenecer a la misma unidad.' using errcode = 'check_violation';
  end if;
  if v_pago.anulado_en is not null then
    raise exception 'El pago está anulado y no se puede aplicar.' using errcode = 'check_violation';
  end if;
  if v_cargo.anulado_en is not null then
    raise exception 'El cargo está anulado y no admite abonos.' using errcode = 'check_violation';
  end if;
  if v_cargo.monto_clp <= 0 then
    raise exception 'Un cargo negativo (ajuste a favor) no recibe abonos.' using errcode = 'check_violation';
  end if;

  select coalesce(sum(a.monto_clp), 0) into v_aplicado_pago
  from public.aplicaciones_pago a where a.pago_id = new.pago_id and a.anulado_en is null;
  if v_aplicado_pago + new.monto_clp > v_pago.monto_clp then
    raise exception 'La suma aplicada supera el monto del pago.' using errcode = 'check_violation';
  end if;

  select coalesce(sum(a.monto_clp), 0) into v_aplicado_cargo
  from public.aplicaciones_pago a where a.cargo_id = new.cargo_id and a.anulado_en is null;
  if v_aplicado_cargo + new.monto_clp > v_cargo.monto_clp then
    raise exception 'La suma aplicada supera el monto del cargo.' using errcode = 'check_violation';
  end if;
  return new;
end;
$$;

create trigger aplicaciones_pago_control
  before insert on public.aplicaciones_pago
  for each row execute function public.aplicaciones_pago_control();

-- Al anular un pago se anulan sus aplicaciones, de modo que la deuda vuelva exacta.
create function public.pagos_anulacion_en_cascada()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  if old.anulado_en is null and new.anulado_en is not null then
    update public.aplicaciones_pago a
    set anulado_en = new.anulado_en,
        anulado_por = new.anulado_por,
        motivo = 'Pago anulado: ' || new.motivo
    where a.pago_id = new.id and a.anulado_en is null;
  end if;
  return null;
end;
$$;

create trigger pagos_anulacion_en_cascada
  after update on public.pagos
  for each row execute function public.pagos_anulacion_en_cascada();

create trigger pagos_solo_anulacion before update on public.pagos
  for each row execute function public.impedir_edicion_salvo_anulacion();
create trigger aplicaciones_pago_solo_anulacion before update on public.aplicaciones_pago
  for each row execute function public.impedir_edicion_salvo_anulacion();

-- De una línea de cartola solo cambia su conciliación.
create function public.movimientos_cartola_control()
returns trigger
language plpgsql
set search_path = ''
as $$
declare
  v_columnas constant text[] := array['estado', 'pago_id', 'gasto_id'];
begin
  if (to_jsonb(old) - v_columnas) is distinct from (to_jsonb(new) - v_columnas) then
    raise exception 'Una línea de cartola importada no se edita; solo se concilia o se ignora.'
      using errcode = 'restrict_violation';
  end if;
  return new;
end;
$$;

create trigger movimientos_cartola_control before update on public.movimientos_cartola
  for each row execute function public.movimientos_cartola_control();

create trigger pagos_sin_delete before delete on public.pagos
  for each row execute function public.impedir_borrado();
create trigger aplicaciones_pago_sin_delete before delete on public.aplicaciones_pago
  for each row execute function public.impedir_borrado();
create trigger movimientos_cartola_sin_delete before delete on public.movimientos_cartola
  for each row execute function public.impedir_borrado();

create trigger pagos_auditoria after insert or update on public.pagos
  for each row execute function public.registrar_auditoria();
create trigger aplicaciones_pago_auditoria after insert or update on public.aplicaciones_pago
  for each row execute function public.registrar_auditoria();
create trigger movimientos_cartola_auditoria after insert or update on public.movimientos_cartola
  for each row execute function public.registrar_auditoria();

-- ---------------------------------------------------------------------------
-- RLS
-- ---------------------------------------------------------------------------

alter table public.pagos enable row level security;
alter table public.aplicaciones_pago enable row level security;
alter table public.movimientos_cartola enable row level security;

grant select on public.pagos, public.aplicaciones_pago, public.movimientos_cartola to authenticated;

create policy "pagos: equipo lee" on public.pagos
  for select to authenticated using (public.es_miembro_org(organizacion_id));
create policy "pagos: comite lee" on public.pagos
  for select to authenticated
  using (public.tiene_acceso_comunidad(comunidad_id, array['comite']));
create policy "pagos: residente lee los de su unidad" on public.pagos
  for select to authenticated using (public.es_residente_unidad(unidad_id));

create policy "aplicaciones_pago: equipo lee" on public.aplicaciones_pago
  for select to authenticated using (public.es_miembro_org(organizacion_id));
create policy "aplicaciones_pago: comite lee" on public.aplicaciones_pago
  for select to authenticated
  using (public.tiene_acceso_comunidad(comunidad_id, array['comite']));
create policy "aplicaciones_pago: residente lee las de su unidad" on public.aplicaciones_pago
  for select to authenticated using (public.es_residente_unidad(unidad_id));

-- La cartola es del equipo: contiene movimientos bancarios de terceros.
create policy "movimientos_cartola: equipo lee" on public.movimientos_cartola
  for select to authenticated using (public.es_miembro_org(organizacion_id));
