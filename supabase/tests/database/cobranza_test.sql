-- pagos, aplicaciones_pago y movimientos_cartola (sección 8: pagos y aplicación de abonos).
begin;
select plan(34);
select tests.crear_escenario();

-- Aislamiento y permisos de lectura.
select tests.como('user_a1');
select is((select count(*) from public.pagos), 2::bigint, 'A ve sus pagos');
select is((select count(*) from public.aplicaciones_pago), 2::bigint, 'A ve sus aplicaciones');
select is((select count(*) from public.movimientos_cartola), 1::bigint, 'A ve su cartola');
select is((select count(*) from public.pagos where organizacion_id = tests.u('org_b')), 0::bigint, 'A no ve pagos de B');
select is((select count(*) from public.aplicaciones_pago where organizacion_id = tests.u('org_b')), 0::bigint, 'A no ve aplicaciones de B');
select is((select count(*) from public.movimientos_cartola where organizacion_id = tests.u('org_b')), 0::bigint, 'A no ve la cartola de B');
select throws_ok($$ insert into public.pagos (organizacion_id, comunidad_id, unidad_id, monto_clp, fecha_pago, medio)
  values (tests.u('org_a'), tests.u('com_a'), tests.u('u_a101'), 1000, current_date, 'efectivo') $$,
  '42501', null, 'el equipo no registra pagos desde la web: lo hace la API');
select tests.como('user_b1');
select is((select count(*) from public.pagos), 1::bigint, 'B ve solo sus pagos');
select tests.como('user_ca');
select is((select count(*) from public.pagos), 2::bigint, 'el comité ve los pagos de su comunidad');
select is((select count(*) from public.aplicaciones_pago), 2::bigint, 'el comité ve las aplicaciones');
select is((select count(*) from public.movimientos_cartola), 0::bigint, 'el comité no ve la cartola bancaria');
select tests.como('user_ra1');
select is((select array_agg(id) from public.pagos), array[tests.u('pago_a')], 'el residente ve solo los pagos de su unidad');
select is((select array_agg(id) from public.aplicaciones_pago), array[tests.u('ap_a')], 'el residente ve solo las aplicaciones de su unidad');
select is((select count(*) from public.movimientos_cartola), 0::bigint, 'el residente no ve la cartola');
select tests.como('user_rb');
select is((select count(*) from public.pagos where unidad_id = tests.u('u_a101')), 0::bigint, 'el residente de B no ve pagos de A');

-- Reglas de aplicación.
select tests.como_api();
select throws_ok($$ insert into public.aplicaciones_pago (organizacion_id, comunidad_id, unidad_id, pago_id, cargo_id, monto_clp)
  values (tests.u('org_a'), tests.u('com_a'), tests.u('u_a101'), tests.u('pago_a'), tests.u('cargo_a101'), 1) $$,
  '23514', null, 'la suma aplicada no supera el pago');
insert into public.pagos (id, organizacion_id, comunidad_id, unidad_id, monto_clp, fecha_pago, medio)
values (tests.u('pago_a_grande'), tests.u('org_a'), tests.u('com_a'), tests.u('u_a101'), 900000, date '2026-09-20', 'transferencia');
select throws_ok($$ insert into public.aplicaciones_pago (organizacion_id, comunidad_id, unidad_id, pago_id, cargo_id, monto_clp)
  values (tests.u('org_a'), tests.u('com_a'), tests.u('u_a101'), tests.u('pago_a_grande'), tests.u('cargo_a101'), 200001) $$,
  '23514', null, 'la suma aplicada no supera el cargo (500.000 con 300.000 ya abonados)');
select lives_ok($$ insert into public.aplicaciones_pago (organizacion_id, comunidad_id, unidad_id, pago_id, cargo_id, monto_clp)
  values (tests.u('org_a'), tests.u('com_a'), tests.u('u_a101'), tests.u('pago_a_grande'), tests.u('cargo_a101'), 200000) $$,
  'se puede completar el cargo exacto');
select throws_ok($$ insert into public.aplicaciones_pago (organizacion_id, comunidad_id, unidad_id, pago_id, cargo_id, monto_clp)
  values (tests.u('org_a'), tests.u('com_a'), tests.u('u_a101'), tests.u('pago_a_grande'), tests.u('cargo_a102'), 1000) $$,
  '23514', null, 'un pago no se aplica a cargos de otra unidad');
select throws_ok($$ insert into public.aplicaciones_pago (organizacion_id, comunidad_id, unidad_id, pago_id, cargo_id, monto_clp)
  values (tests.u('org_b'), tests.u('com_b'), tests.u('u_b201'), tests.u('pago_a_grande'), tests.u('cargo_b201'), 1000) $$,
  '23514', null, 'un pago de A no se aplica a una unidad de B');

-- Anular un pago restituye la deuda exacta.
select is(
  (select c.monto_clp - coalesce(sum(a.monto_clp) filter (where a.anulado_en is null), 0)
   from public.cargos c left join public.aplicaciones_pago a on a.cargo_id = c.id
   where c.id = tests.u('cargo_a101') group by c.monto_clp),
  0::bigint, 'con los pagos aplicados el cargo está saldado');
select throws_ok($$ update public.pagos set anulado_en = now(), anulado_por = tests.u('user_a1') where id = tests.u('pago_a') $$,
  '23514', null, 'anular un pago exige motivo');
select lives_ok($$ update public.pagos set anulado_en = now(), anulado_por = tests.u('user_a1'), motivo = 'Cheque protestado'
  where id = tests.u('pago_a') $$, 'se anula un pago con motivo');
select is((select count(*) from public.aplicaciones_pago where pago_id = tests.u('pago_a') and anulado_en is null),
  0::bigint, 'al anular el pago se anulan sus aplicaciones');
select is(
  (select c.monto_clp - coalesce(sum(a.monto_clp) filter (where a.anulado_en is null), 0)
   from public.cargos c left join public.aplicaciones_pago a on a.cargo_id = c.id
   where c.id = tests.u('cargo_a101') group by c.monto_clp),
  300000::bigint, 'la deuda se restituye en 300.000, exactamente lo que cubría el pago anulado');
select throws_ok($$ insert into public.aplicaciones_pago (organizacion_id, comunidad_id, unidad_id, pago_id, cargo_id, monto_clp)
  values (tests.u('org_a'), tests.u('com_a'), tests.u('u_a101'), tests.u('pago_a'), tests.u('cargo_a101'), 1) $$,
  '23514', null, 'un pago anulado no se aplica');
select throws_ok($$ update public.pagos set monto_clp = 1 where id = tests.u('pago_a102') $$,
  '23001', null, 'el monto de un pago no se edita');
select throws_ok($$ update public.pagos set motivo = 'reescrito' where id = tests.u('pago_a') $$,
  '23001', null, 'una anulación no se reescribe');
select throws_ok($$ delete from public.pagos where id = tests.u('pago_a102') $$, '23001', null, 'los pagos no se borran');
select throws_ok($$ delete from public.aplicaciones_pago where id = tests.u('ap_a102') $$, '23001', null, 'las aplicaciones no se borran');
select throws_ok($$ insert into public.pagos (organizacion_id, comunidad_id, unidad_id, monto_clp, fecha_pago, medio)
  values (tests.u('org_a'), tests.u('com_a'), tests.u('u_a101'), 0, current_date, 'efectivo') $$,
  '23514', null, 'un pago tiene monto positivo');

-- Cartola.
select throws_ok($$ insert into public.movimientos_cartola (organizacion_id, comunidad_id, fecha, descripcion, monto_clp, hash)
  values (tests.u('org_a'), tests.u('com_a'), current_date, 'Duplicado', 300000, 'hash-a') $$,
  '23505', null, 'la misma línea de cartola no se importa dos veces');
select throws_ok($$ update public.movimientos_cartola set monto_clp = 1 where id = tests.u('mov_a') $$,
  '23001', null, 'una línea importada no se edita');
select lives_ok($$ update public.movimientos_cartola set estado = 'conciliado', pago_id = tests.u('pago_a102')
  where id = tests.u('mov_a') $$, 'se concilia una línea con un pago');

select * from finish();
rollback;
