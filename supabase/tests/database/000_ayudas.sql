-- Ayudas compartidas por las pruebas pgTAP. Este archivo se confirma (commit) a propósito para que
-- el esquema `tests` exista en las demás pruebas; cada una corre dentro de su transacción y la revierte.
-- Solo vive en la base local de pruebas: `supabase db reset` lo elimina.
begin;
select plan(1);

create schema if not exists tests;
grant usage on schema tests to public;

-- Identificador estable a partir de un nombre legible: tests.u('org_a').
create or replace function tests.u(p_nombre text) returns uuid
language sql immutable as $$ select md5('sgch:' || p_nombre)::uuid $$;

-- Simula una sesión autenticada de la web (JWT con ese usuario) o anónima.
create or replace function tests.como(p_usuario text) returns void
language plpgsql as $$
begin
  perform set_config('request.jwt.claims',
    json_build_object('sub', tests.u(p_usuario), 'role', 'authenticated')::text, true);
  set local role authenticated;
end $$;

create or replace function tests.como_anonimo() returns void
language plpgsql as $$
begin
  perform set_config('request.jwt.claims', json_build_object('role', 'anon')::text, true);
  set local role anon;
end $$;

-- Vuelve al rol de la API (omite RLS).
create or replace function tests.como_api() returns void
language plpgsql as $$
begin
  reset role;
  perform set_config('request.jwt.claims', '', true);
end $$;

grant execute on all functions in schema tests to public;

-- Escenario: dos organizaciones, cada una con una comunidad y una fila en cada tabla.
--   Org A: usuarios user_a1 (owner) y user_a2 (staff); comunidad com_a (unidades u_a101 y u_a102,
--          comité user_ca, residentes user_ra1 y user_ra2) y com_a2 (solo unidad u_a2_1).
--          Período ago-2026 emitido y sep-2026 abierto.
--   Org B: user_b1 (owner); comunidad com_b con u_b201, comité user_cb y residente user_rb.
--   user_x no pertenece a ninguna.
create or replace function tests.crear_escenario() returns void
language plpgsql as $$
declare
  v_ago date := date '2026-08-01';
  v_sep date := date '2026-09-01';
begin
  perform tests.como_api();

  insert into auth.users (id, aud, role, email)
  select tests.u(n), 'authenticated', 'authenticated', n || '@sgch.test'
  from unnest(array['user_a1', 'user_a2', 'user_b1', 'user_ca', 'user_cb', 'user_ra1', 'user_ra2',
                    'user_rb', 'user_x']) as n;

  insert into public.organizaciones (id, nombre) values
    (tests.u('org_a'), 'Administraciones Ficticias A'), (tests.u('org_b'), 'Administraciones Ficticias B');
  insert into public.miembros_organizacion (organizacion_id, usuario_id, rol) values
    (tests.u('org_a'), tests.u('user_a1'), 'owner'), (tests.u('org_a'), tests.u('user_a2'), 'staff'),
    (tests.u('org_b'), tests.u('user_b1'), 'owner');

  insert into public.comunidades (id, organizacion_id, nombre, rut) values
    (tests.u('com_a'), tests.u('org_a'), 'Mirador A', '76111111-1'),
    (tests.u('com_a2'), tests.u('org_a'), 'Parque A2', '76222222-2'),
    (tests.u('com_b'), tests.u('org_b'), 'Mirador B', '76333333-3');

  insert into public.unidades (id, organizacion_id, comunidad_id, codigo, prorrateo) values
    (tests.u('u_a101'), tests.u('org_a'), tests.u('com_a'), 'A-101', 0.5),
    (tests.u('u_a102'), tests.u('org_a'), tests.u('com_a'), 'A-102', 0.5),
    (tests.u('u_a2_1'), tests.u('org_a'), tests.u('com_a2'), 'P-1', 1),
    (tests.u('u_b201'), tests.u('org_b'), tests.u('com_b'), 'B-201', 1);

  insert into public.accesos_comunidad (organizacion_id, comunidad_id, usuario_id, rol, unidad_id) values
    (tests.u('org_a'), tests.u('com_a'), tests.u('user_ca'), 'comite', null),
    (tests.u('org_a'), tests.u('com_a'), tests.u('user_ra1'), 'residente', tests.u('u_a101')),
    (tests.u('org_a'), tests.u('com_a'), tests.u('user_ra2'), 'residente', tests.u('u_a102')),
    (tests.u('org_b'), tests.u('com_b'), tests.u('user_cb'), 'comite', null),
    (tests.u('org_b'), tests.u('com_b'), tests.u('user_rb'), 'residente', tests.u('u_b201'));

  insert into public.personas (id, organizacion_id, nombre) values
    (tests.u('persona_a'), tests.u('org_a'), 'Persona Ficticia A'),
    (tests.u('persona_a2'), tests.u('org_a'), 'Persona Ficticia A102'),
    (tests.u('persona_b'), tests.u('org_b'), 'Persona Ficticia B');
  insert into public.unidad_personas (id, organizacion_id, comunidad_id, unidad_id, persona_id, rol, desde) values
    (tests.u('up_a'), tests.u('org_a'), tests.u('com_a'), tests.u('u_a101'), tests.u('persona_a'), 'propietario', v_ago),
    (tests.u('up_a2'), tests.u('org_a'), tests.u('com_a'), tests.u('u_a102'), tests.u('persona_a2'), 'propietario', v_ago),
    (tests.u('up_b'), tests.u('org_b'), tests.u('com_b'), tests.u('u_b201'), tests.u('persona_b'), 'propietario', v_ago);
  insert into public.proveedores (id, organizacion_id, comunidad_id, nombre) values
    (tests.u('prov_a'), tests.u('org_a'), tests.u('com_a'), 'Ascensores Ficticios A'),
    (tests.u('prov_b'), tests.u('org_b'), tests.u('com_b'), 'Ascensores Ficticios B');
  insert into public.grupos_prorrateo (id, organizacion_id, comunidad_id, nombre) values
    (tests.u('grupo_a'), tests.u('org_a'), tests.u('com_a'), 'Torre A'),
    (tests.u('grupo_b'), tests.u('org_b'), tests.u('com_b'), 'Torre B');
  insert into public.grupo_prorrateo_unidades (id, organizacion_id, comunidad_id, grupo_id, unidad_id, prorrateo) values
    (tests.u('gpu_a'), tests.u('org_a'), tests.u('com_a'), tests.u('grupo_a'), tests.u('u_a101'), 1),
    (tests.u('gpu_b'), tests.u('org_b'), tests.u('com_b'), tests.u('grupo_b'), tests.u('u_b201'), 1);

  -- Org A, agosto: gasto y cargos; luego se cierra y se emite.
  insert into public.periodos (id, organizacion_id, comunidad_id, mes) values
    (tests.u('per_a_ago'), tests.u('org_a'), tests.u('com_a'), v_ago),
    (tests.u('per_a_sep'), tests.u('org_a'), tests.u('com_a'), v_sep),
    (tests.u('per_b_sep'), tests.u('org_b'), tests.u('com_b'), v_sep);
  insert into public.gastos (id, organizacion_id, comunidad_id, periodo_id, tipo, categoria, descripcion, monto_clp, fecha) values
    (tests.u('gasto_a_ago'), tests.u('org_a'), tests.u('com_a'), tests.u('per_a_ago'), 'ordinario', 'administracion', 'Honorarios', 1000000, v_ago),
    (tests.u('gasto_a_sep'), tests.u('org_a'), tests.u('com_a'), tests.u('per_a_sep'), 'ordinario', 'mantencion', 'Aseo', 200000, v_sep),
    (tests.u('gasto_b'), tests.u('org_b'), tests.u('com_b'), tests.u('per_b_sep'), 'ordinario', 'administracion', 'Honorarios', 100000, v_sep);
  insert into public.cargos (id, organizacion_id, comunidad_id, periodo_id, unidad_id, concepto, monto_clp, vencimiento) values
    (tests.u('cargo_a101'), tests.u('org_a'), tests.u('com_a'), tests.u('per_a_ago'), tests.u('u_a101'), 'gasto_comun', 500000, date '2026-09-10'),
    (tests.u('cargo_a102'), tests.u('org_a'), tests.u('com_a'), tests.u('per_a_ago'), tests.u('u_a102'), 'gasto_comun', 500000, date '2026-09-10'),
    (tests.u('cargo_a101_multa'), tests.u('org_a'), tests.u('com_a'), tests.u('per_a_sep'), tests.u('u_a101'), 'multa', 10000, date '2026-10-10'),
    (tests.u('cargo_b201'), tests.u('org_b'), tests.u('com_b'), tests.u('per_b_sep'), tests.u('u_b201'), 'gasto_comun', 100000, date '2026-10-10');
  update public.periodos set estado = 'cerrado', cerrado_en = now(), cerrado_por = tests.u('user_a1')
  where id = tests.u('per_a_ago');
  update public.periodos set estado = 'emitido', emitido_en = now() where id = tests.u('per_a_ago');

  insert into public.pagos (id, organizacion_id, comunidad_id, unidad_id, monto_clp, fecha_pago, medio) values
    (tests.u('pago_a'), tests.u('org_a'), tests.u('com_a'), tests.u('u_a101'), 300000, date '2026-09-05', 'transferencia'),
    (tests.u('pago_a102'), tests.u('org_a'), tests.u('com_a'), tests.u('u_a102'), 500000, date '2026-09-06', 'transferencia'),
    (tests.u('pago_b'), tests.u('org_b'), tests.u('com_b'), tests.u('u_b201'), 100000, date '2026-09-06', 'transferencia');
  insert into public.aplicaciones_pago (id, organizacion_id, comunidad_id, unidad_id, pago_id, cargo_id, monto_clp) values
    (tests.u('ap_a'), tests.u('org_a'), tests.u('com_a'), tests.u('u_a101'), tests.u('pago_a'), tests.u('cargo_a101'), 300000),
    (tests.u('ap_a102'), tests.u('org_a'), tests.u('com_a'), tests.u('u_a102'), tests.u('pago_a102'), tests.u('cargo_a102'), 500000),
    (tests.u('ap_b'), tests.u('org_b'), tests.u('com_b'), tests.u('u_b201'), tests.u('pago_b'), tests.u('cargo_b201'), 100000);
  insert into public.movimientos_cartola (id, organizacion_id, comunidad_id, fecha, descripcion, monto_clp, hash) values
    (tests.u('mov_a'), tests.u('org_a'), tests.u('com_a'), v_sep, 'Transferencia ficticia', 300000, 'hash-a'),
    (tests.u('mov_b'), tests.u('org_b'), tests.u('com_b'), v_sep, 'Transferencia ficticia', 100000, 'hash-b');
  insert into public.fondo_reserva_movimientos (id, organizacion_id, comunidad_id, tipo, monto_clp, fecha) values
    (tests.u('fondo_a'), tests.u('org_a'), tests.u('com_a'), 'aporte', 50000, v_ago),
    (tests.u('fondo_b'), tests.u('org_b'), tests.u('com_b'), 'aporte', 5000, v_sep);
  insert into public.rendiciones (id, organizacion_id, comunidad_id, periodo_id) values
    (tests.u('rend_a'), tests.u('org_a'), tests.u('com_a'), tests.u('per_a_ago')),
    (tests.u('rend_b'), tests.u('org_b'), tests.u('com_b'), tests.u('per_b_sep'));

  insert into public.documentos (id, organizacion_id, comunidad_id, tipo, nombre, ruta_storage, visible_residentes) values
    (tests.u('doc_a'), tests.u('org_a'), tests.u('com_a'), 'reglamento', 'Reglamento',
       tests.u('org_a') || '/' || tests.u('com_a') || '/documentos/reglamento.pdf', true),
    (tests.u('doc_a_privado'), tests.u('org_a'), tests.u('com_a'), 'contrato', 'Contrato',
       tests.u('org_a') || '/' || tests.u('com_a') || '/documentos/contrato.pdf', false),
    (tests.u('doc_b'), tests.u('org_b'), tests.u('com_b'), 'reglamento', 'Reglamento',
       tests.u('org_b') || '/' || tests.u('com_b') || '/documentos/reglamento.pdf', true);
  insert into storage.objects (bucket_id, name) values
    ('documentos', tests.u('org_a') || '/' || tests.u('com_a') || '/documentos/reglamento.pdf'),
    ('documentos', tests.u('org_b') || '/' || tests.u('com_b') || '/documentos/reglamento.pdf');
end $$;

select pass('ayudas de prueba creadas');
select * from finish();
commit;
