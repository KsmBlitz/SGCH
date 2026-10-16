-- fondo_reserva_movimientos y rendiciones (sección 8: fondo de reserva; art. 39 [verificar]).
begin;
select plan(23);
select tests.crear_escenario();

select tests.como('user_a1');
select is((select count(*) from public.fondo_reserva_movimientos), 1::bigint, 'A ve el fondo de su comunidad');
select is((select count(*) from public.fondo_reserva_movimientos where organizacion_id = tests.u('org_b')), 0::bigint, 'A no ve el fondo de B');
select is((select count(*) from public.rendiciones), 1::bigint, 'A ve sus rendiciones');
select is((select count(*) from public.rendiciones where organizacion_id = tests.u('org_b')), 0::bigint, 'A no ve rendiciones de B');
select throws_ok($$ insert into public.fondo_reserva_movimientos (organizacion_id, comunidad_id, tipo, monto_clp, fecha)
  values (tests.u('org_a'), tests.u('com_a'), 'aporte', 1000, current_date) $$, '42501', null,
  'el equipo no escribe el fondo desde la web');
select throws_ok($$ update public.rendiciones set estado = 'aprobada' $$, '42501', null, 'el equipo no aprueba rendiciones');
select tests.como('user_b1');
select is((select count(*) from public.fondo_reserva_movimientos), 1::bigint, 'B ve solo su fondo');
select tests.como('user_ca');
select is((select count(*) from public.fondo_reserva_movimientos), 1::bigint, 'el comité ve el fondo');
select is((select count(*) from public.rendiciones), 1::bigint, 'el comité ve la rendición');
select throws_ok($$ update public.rendiciones set estado = 'aprobada', aprobado_por = tests.u('user_ca'), aprobado_en = now() $$,
  '42501', null, 'el comité aprueba por la API (que registra su usuario), no escribiendo directo');
select tests.como('user_ra1');
select is((select count(*) from public.fondo_reserva_movimientos), 0::bigint, 'el residente no ve el fondo');
select is((select count(*) from public.rendiciones), 0::bigint, 'el residente no ve rendiciones');
select tests.como('user_rb');
select is((select count(*) from public.fondo_reserva_movimientos), 0::bigint, 'el residente de B no ve el fondo de A ni el de B');

-- Reglas del fondo (como la API).
select tests.como_api();
select throws_ok($$ insert into public.fondo_reserva_movimientos (organizacion_id, comunidad_id, tipo, monto_clp, fecha)
  values (tests.u('org_a'), tests.u('com_a'), 'uso', 1000, current_date) $$, '23514', null,
  'el uso exige descripción y comprobante');
select throws_ok($$ insert into public.fondo_reserva_movimientos (organizacion_id, comunidad_id, tipo, monto_clp, fecha, descripcion, comprobante_path)
  values (tests.u('org_a'), tests.u('com_a'), 'uso', 60000, current_date, 'Bomba de agua', 'a/b/comprobantes/f.pdf') $$,
  '23514', null, 'el uso no supera el saldo (50.000)');
select lives_ok($$ insert into public.fondo_reserva_movimientos (id, organizacion_id, comunidad_id, tipo, monto_clp, fecha, descripcion, comprobante_path)
  values (tests.u('uso_a'), tests.u('org_a'), tests.u('com_a'), 'uso', 20000, current_date, 'Bomba de agua', 'a/b/comprobantes/f.pdf') $$,
  'un uso dentro del saldo es válido');
select throws_ok($$ update public.fondo_reserva_movimientos set anulado_en = now(), anulado_por = tests.u('user_a1'), motivo = 'Error'
  where id = tests.u('fondo_a') $$, '23514', null, 'anular el aporte dejaría el saldo negativo');
select lives_ok($$ update public.fondo_reserva_movimientos set anulado_en = now(), anulado_por = tests.u('user_a1'), motivo = 'Error'
  where id = tests.u('uso_a') $$, 'se puede anular un uso y el saldo vuelve');
select throws_ok($$ update public.fondo_reserva_movimientos set monto_clp = 1 where id = tests.u('fondo_a') $$,
  '23001', null, 'los movimientos del fondo no se editan');
select throws_ok($$ delete from public.fondo_reserva_movimientos where id = tests.u('fondo_a') $$, '23001', null,
  'los movimientos del fondo no se borran');

-- Rendiciones.
select throws_ok($$ update public.rendiciones set estado = 'aprobada' where id = tests.u('rend_a') $$, '23514', null,
  'aprobar exige usuario y fecha de aprobación');
select throws_ok($$ insert into public.rendiciones (organizacion_id, comunidad_id, periodo_id)
  values (tests.u('org_a'), tests.u('com_a'), tests.u('per_a_ago')) $$, '23505', null, 'una rendición por período');
select throws_ok($$ delete from public.rendiciones where id = tests.u('rend_a') $$, '23001', null, 'las rendiciones no se borran');

select * from finish();
rollback;
