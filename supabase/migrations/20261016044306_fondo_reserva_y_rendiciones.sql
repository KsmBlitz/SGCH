-- Fondo de reserva y rendiciones (secciones 8 y 10).

-- Aportes y usos del fondo. El saldo se calcula: aportes vigentes menos usos vigentes.
-- Destino de intereses y multas y art. 39 de la Ley 21.442 [verificar].
create table public.fondo_reserva_movimientos (
  id                uuid primary key default gen_random_uuid(),
  organizacion_id   uuid not null,
  comunidad_id      uuid not null,
  tipo              text not null check (tipo in ('aporte', 'uso')),
  monto_clp         integer not null check (monto_clp > 0),
  fecha             date not null,
  periodo_id        uuid,
  -- Cargo (reserva, interés o multa) que alimentó el fondo.
  cargo_id          uuid,
  -- Gasto que se financió con el fondo.
  gasto_id          uuid,
  -- Para qué se usó el fondo. No confundir con `motivo`, que explica una anulación.
  descripcion       text,
  comprobante_path  text,
  anulado_en        timestamptz,
  anulado_por       uuid references auth.users (id),
  motivo            text,
  creado_en         timestamptz not null default now(),
  creado_por        uuid references auth.users (id),
  foreign key (comunidad_id, organizacion_id) references public.comunidades (id, organizacion_id),
  foreign key (periodo_id, comunidad_id) references public.periodos (id, comunidad_id),
  foreign key (cargo_id, comunidad_id) references public.cargos (id, comunidad_id),
  foreign key (gasto_id, comunidad_id) references public.gastos (id, comunidad_id),
  -- El uso exige motivo y comprobante (sección 8).
  check (
    tipo = 'aporte'
    or (coalesce(length(trim(descripcion)), 0) > 0 and coalesce(length(trim(comprobante_path)), 0) > 0)
  ),
  constraint fondo_reserva_movimientos_anulacion_con_motivo
    check (anulado_en is null or (anulado_por is not null and coalesce(length(trim(motivo)), 0) > 0))
);

create index fondo_reserva_movimientos_comunidad_idx on public.fondo_reserva_movimientos (comunidad_id, fecha);

-- El fondo nunca queda con saldo negativo, ni por un uso ni por anular un aporte.
create function public.fondo_reserva_saldo_no_negativo()
returns trigger
language plpgsql
set search_path = ''
as $$
declare
  v_saldo bigint;
begin
  -- Serializa los movimientos de una misma comunidad.
  perform pg_advisory_xact_lock(hashtextextended('fondo_reserva:' || new.comunidad_id::text, 0));

  select coalesce(sum(case m.tipo when 'aporte' then m.monto_clp else -m.monto_clp end), 0)
  into v_saldo
  from public.fondo_reserva_movimientos m
  where m.comunidad_id = new.comunidad_id and m.anulado_en is null;

  if v_saldo < 0 then
    raise exception 'El fondo de reserva no puede quedar con saldo negativo.'
      using errcode = 'check_violation';
  end if;
  return null;
end;
$$;

create trigger fondo_reserva_saldo_no_negativo
  after insert or update on public.fondo_reserva_movimientos
  for each row execute function public.fondo_reserva_saldo_no_negativo();

create trigger fondo_reserva_movimientos_solo_anulacion
  before update on public.fondo_reserva_movimientos
  for each row execute function public.impedir_edicion_salvo_anulacion();
create trigger fondo_reserva_movimientos_sin_delete
  before delete on public.fondo_reserva_movimientos
  for each row execute function public.impedir_borrado();
create trigger fondo_reserva_movimientos_auditoria
  after insert or update on public.fondo_reserva_movimientos
  for each row execute function public.registrar_auditoria();

create table public.rendiciones (
  id                uuid primary key default gen_random_uuid(),
  organizacion_id   uuid not null,
  comunidad_id      uuid not null,
  periodo_id        uuid not null,
  estado            text not null default 'borrador'
                    check (estado in ('borrador', 'enviada', 'aprobada', 'observada')),
  enviada_en        timestamptz,
  aprobado_por      uuid references auth.users (id),
  aprobado_en       timestamptz,
  comentarios       text,
  creado_en         timestamptz not null default now(),
  foreign key (comunidad_id, organizacion_id) references public.comunidades (id, organizacion_id),
  foreign key (periodo_id, comunidad_id) references public.periodos (id, comunidad_id),
  unique (periodo_id),
  check ((estado = 'borrador') = (enviada_en is null)),
  check ((estado = 'aprobada') = (aprobado_por is not null and aprobado_en is not null))
);

create index rendiciones_comunidad_idx on public.rendiciones (comunidad_id);

create trigger rendiciones_sin_delete before delete on public.rendiciones
  for each row execute function public.impedir_borrado();
create trigger rendiciones_auditoria after insert or update on public.rendiciones
  for each row execute function public.registrar_auditoria();

alter table public.fondo_reserva_movimientos enable row level security;
alter table public.rendiciones enable row level security;

grant select on public.fondo_reserva_movimientos, public.rendiciones to authenticated;

create policy "fondo_reserva_movimientos: equipo lee" on public.fondo_reserva_movimientos
  for select to authenticated using (public.es_miembro_org(organizacion_id));
create policy "fondo_reserva_movimientos: comite lee" on public.fondo_reserva_movimientos
  for select to authenticated
  using (public.tiene_acceso_comunidad(comunidad_id, array['comite']));

-- La aprobación del comité la registra la API con el usuario del comité (POST /rendiciones/{id}/aprobar).
create policy "rendiciones: equipo lee" on public.rendiciones
  for select to authenticated using (public.es_miembro_org(organizacion_id));
create policy "rendiciones: comite lee" on public.rendiciones
  for select to authenticated
  using (public.tiene_acceso_comunidad(comunidad_id, array['comite']));
