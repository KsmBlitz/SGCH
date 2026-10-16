-- periodos, gastos y cargos: aislamiento, permisos por rol y reglas del ciclo mensual (sección 8).
begin;
select plan(44);
select tests.crear_escenario();

-- Equipo A y B.
select tests.como('user_a2');
select is((select count(*) from public.periodos), 2::bigint, 'A ve sus períodos');
select is((select count(*) from public.gastos), 2::bigint, 'A ve sus gastos');
select is((select count(*) from public.cargos), 3::bigint, 'A ve sus cargos');
select is((select count(*) from public.cargos where organizacion_id = tests.u('org_b')), 0::bigint, 'A no ve cargos de B');
select is((select count(*) from public.gastos where organizacion_id = tests.u('org_b')), 0::bigint, 'A no ve gastos de B');
select is((select count(*) from public.periodos where organizacion_id = tests.u('org_b')), 0::bigint, 'A no ve períodos de B');
select throws_ok($$ insert into public.gastos (organizacion_id, comunidad_id, periodo_id, tipo, categoria, descripcion, monto_clp, fecha)
  values (tests.u('org_a'), tests.u('com_a'), tests.u('per_a_sep'), 'ordinario', 'mantencion', 'X', 1000, current_date) $$,
  '42501', null, 'el equipo no escribe gastos desde la web');
select throws_ok($$ update public.cargos set monto_clp = 1 $$, '42501', null, 'el equipo no modifica cargos desde la web');
select tests.como('user_b1');
select is((select count(*) from public.cargos), 1::bigint, 'B ve solo sus cargos');
select is((select count(*) from public.gastos), 1::bigint, 'B ve solo sus gastos');

-- Comité: lee todo su período, incluidos cargos aún no emitidos.
select tests.como('user_ca');
select is((select count(*) from public.periodos), 2::bigint, 'el comité ve los períodos');
select is((select count(*) from public.gastos), 2::bigint, 'el comité ve los gastos');
select is((select count(*) from public.cargos), 3::bigint, 'el comité ve los cargos de su comunidad');
select throws_ok($$ update public.gastos set monto_clp = 1 $$, '42501', null, 'el comité no escribe dinero');

-- Residente: solo cargos emitidos de su unidad, sin gastos.
select tests.como('user_ra1');
select is((select count(*) from public.periodos), 2::bigint, 'el residente ve los períodos');
select is((select count(*) from public.gastos), 0::bigint, 'el residente no ve gastos');
select is((select array_agg(id) from public.cargos), array[tests.u('cargo_a101')],
  'el residente ve su cargo emitido y no la multa del período abierto');
select tests.como('user_ra2');
select is((select array_agg(id) from public.cargos), array[tests.u('cargo_a102')], 'el residente 2 ve solo el cargo de su unidad');
select tests.como('user_rb');
select is((select count(*) from public.cargos where unidad_id = tests.u('u_a101')), 0::bigint, 'el residente de B no ve unidades de A');

-- Período emitido: inmutable (ADR 0007).
select tests.como_api();
select throws_ok($$ insert into public.gastos (organizacion_id, comunidad_id, periodo_id, tipo, categoria, descripcion, monto_clp, fecha)
  values (tests.u('org_a'), tests.u('com_a'), tests.u('per_a_ago'), 'ordinario', 'mantencion', 'Tarde', 1000, current_date) $$,
  '23001', null, 'no se agregan gastos a un período emitido');
select throws_ok($$ update public.gastos set monto_clp = 1 where id = tests.u('gasto_a_ago') $$,
  '23001', null, 'no se editan gastos de un período emitido');
select throws_ok($$ insert into public.cargos (organizacion_id, comunidad_id, periodo_id, unidad_id, concepto, monto_clp, vencimiento)
  values (tests.u('org_a'), tests.u('com_a'), tests.u('per_a_ago'), tests.u('u_a101'), 'ajuste', -1000, current_date) $$,
  '23001', null, 'las correcciones van como ajuste en el período siguiente, no en el cerrado');
select throws_ok($$ update public.cargos set anulado_en = now(), anulado_por = tests.u('user_a1'), motivo = 'x'
  where id = tests.u('cargo_a101') $$, '23001', null, 'no se anulan cargos de un período cerrado');
select throws_ok($$ update public.periodos set emitido_en = now() + interval '1 day' where id = tests.u('per_a_ago') $$,
  '23001', null, 'un período emitido no se edita');
select throws_ok($$ update public.periodos set estado = 'abierto', cerrado_en = null, cerrado_por = null, emitido_en = null
  where id = tests.u('per_a_ago') $$, '23001', null, 'un período no vuelve a abierto');
select throws_ok($$ update public.periodos set estado = 'emitido', emitido_en = now() where id = tests.u('per_b_sep') $$,
  '23001', null, 'un período abierto no salta directo a emitido');

-- Período abierto: editable hasta el cierre.
select lives_ok($$ update public.gastos set monto_clp = 250000 where id = tests.u('gasto_a_sep') $$,
  'un gasto de un período abierto se edita');
select throws_ok($$ update public.cargos set monto_clp = 1 where id = tests.u('cargo_a101_multa') $$,
  '23001', null, 'un cargo nunca se edita, solo se anula');
select lives_ok($$ update public.cargos set anulado_en = now(), anulado_por = tests.u('user_a1'), motivo = 'Multa mal cursada'
  where id = tests.u('cargo_a101_multa') $$, 'un cargo de un período abierto se anula con motivo');
select throws_ok($$ update public.cargos set motivo = 'otro motivo' where id = tests.u('cargo_a101_multa') $$,
  '23001', null, 'una anulación no se revierte ni se reescribe');

-- Cierre idempotente: un cargo vigente por unidad y concepto.
select lives_ok($$ insert into public.cargos (organizacion_id, comunidad_id, periodo_id, unidad_id, concepto, monto_clp, vencimiento)
  values (tests.u('org_a'), tests.u('com_a'), tests.u('per_a_sep'), tests.u('u_a101'), 'gasto_comun', 100000, date '2026-10-10') $$,
  'el cierre crea el cargo de gasto común');
select throws_ok($$ insert into public.cargos (organizacion_id, comunidad_id, periodo_id, unidad_id, concepto, monto_clp, vencimiento)
  values (tests.u('org_a'), tests.u('com_a'), tests.u('per_a_sep'), tests.u('u_a101'), 'gasto_comun', 100000, date '2026-10-10') $$,
  '23505', null, 'cerrar dos veces no duplica el cargo');
select lives_ok($$ insert into public.cargos (organizacion_id, comunidad_id, periodo_id, unidad_id, concepto, monto_clp, vencimiento)
  values (tests.u('org_a'), tests.u('com_a'), tests.u('per_a_sep'), tests.u('u_a101'), 'ajuste', -5000, date '2026-10-10') $$,
  'un ajuste puede ser negativo');

-- Cierre bloqueado si los prorrateos no suman 1.
update public.unidades set prorrateo = 0.4 where id = tests.u('u_a101');
select throws_ok($$ update public.periodos set estado = 'cerrado', cerrado_en = now(), cerrado_por = tests.u('user_a1')
  where id = tests.u('per_a_sep') $$, '23514', null, 'no cierra si los prorrateos no suman 1');
update public.unidades set prorrateo = 0.5 where id = tests.u('u_a101');

-- Cierre bloqueado si un grupo de prorrateo usado por un extraordinario no suma 1.
insert into public.gastos (organizacion_id, comunidad_id, periodo_id, tipo, categoria, descripcion, monto_clp, fecha,
                           grupo_prorrateo_id, aprobado_en, aprobado_por)
values (tests.u('org_a'), tests.u('com_a'), tests.u('per_a_sep'), 'extraordinario', 'reparacion', 'Fachada torre', 900000,
        current_date, tests.u('grupo_a'), now(), tests.u('user_a1'));
insert into public.grupo_prorrateo_unidades (organizacion_id, comunidad_id, grupo_id, unidad_id, prorrateo)
values (tests.u('org_a'), tests.u('com_a'), tests.u('grupo_a'), tests.u('u_a102'), 0.5);
select throws_ok($$ update public.periodos set estado = 'cerrado', cerrado_en = now(), cerrado_por = tests.u('user_a1')
  where id = tests.u('per_a_sep') $$, '23514', null, 'no cierra si un grupo de prorrateo no suma 1');
delete from public.grupo_prorrateo_unidades where grupo_id = tests.u('grupo_a') and unidad_id = tests.u('u_a102');
select lives_ok($$ update public.periodos set estado = 'cerrado', cerrado_en = now(), cerrado_por = tests.u('user_a1')
  where id = tests.u('per_a_sep') $$, 'cierra cuando todo suma 1');
select throws_ok($$ update public.gastos set monto_clp = 1 where id = tests.u('gasto_a_sep') $$,
  '23001', null, 'tras el cierre los gastos quedan congelados');

-- Checks y claves compuestas.
select throws_ok($$ insert into public.gastos (organizacion_id, comunidad_id, periodo_id, tipo, categoria, descripcion, monto_clp, fecha)
  values (tests.u('org_b'), tests.u('com_b'), tests.u('per_b_sep'), 'ordinario', 'administracion', 'Cero', 0, current_date) $$,
  '23514', null, 'un gasto tiene monto positivo');
select throws_ok($$ insert into public.cargos (organizacion_id, comunidad_id, periodo_id, unidad_id, concepto, monto_clp, vencimiento)
  values (tests.u('org_b'), tests.u('com_b'), tests.u('per_b_sep'), tests.u('u_b201'), 'multa', -1000, current_date) $$,
  '23514', null, 'solo un ajuste puede ser negativo');
select throws_ok($$ insert into public.cargos (organizacion_id, comunidad_id, periodo_id, unidad_id, concepto, monto_clp, vencimiento)
  values (tests.u('org_a'), tests.u('com_a'), tests.u('per_b_sep'), tests.u('u_a101'), 'multa', 1000, current_date) $$,
  '23503', null, 'un cargo no cruza el período de otra comunidad');
select throws_ok($$ insert into public.periodos (organizacion_id, comunidad_id, mes)
  values (tests.u('org_a'), tests.u('com_a'), date '2026-10-15') $$, '23514', null, 'el mes contable es el primer día del mes');
select throws_ok($$ delete from public.cargos where id = tests.u('cargo_a101') $$, '23001', null, 'los cargos no se borran');
select throws_ok($$ delete from public.gastos where id = tests.u('gasto_a_sep') $$, '23001', null, 'los gastos no se borran');
select throws_ok($$ delete from public.periodos where id = tests.u('per_a_sep') $$, '23001', null, 'los períodos no se borran');

select * from finish();
rollback;
