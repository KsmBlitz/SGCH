-- organizaciones, miembros_organizacion, comunidades, unidades y accesos_comunidad.
begin;
select plan(38);
select tests.crear_escenario();

-- Equipo de la organización A.
select tests.como('user_a1');
select is((select count(*) from public.organizaciones), 1::bigint, 'A ve solo su organización');
select is((select count(*) from public.organizaciones where id = tests.u('org_b')), 0::bigint, 'A no ve la organización B');
select is((select count(*) from public.miembros_organizacion), 2::bigint, 'A ve a su equipo (2) y no al de B');
select is((select count(*) from public.comunidades), 2::bigint, 'A ve sus dos comunidades');
select is((select count(*) from public.comunidades where organizacion_id = tests.u('org_b')), 0::bigint, 'A no ve comunidades de B');
select is((select count(*) from public.unidades), 3::bigint, 'A ve las unidades de sus comunidades');
select is((select count(*) from public.unidades where organizacion_id = tests.u('org_b')), 0::bigint, 'A no ve unidades de B');
select is((select count(*) from public.accesos_comunidad), 3::bigint, 'A ve los accesos de sus comunidades');
select is((select count(*) from public.auditoria where organizacion_id = tests.u('org_b')), 0::bigint, 'A no ve la auditoría de B');
select cmp_ok((select count(*) from public.auditoria), '>', 0::bigint, 'A ve su propia auditoría');
select throws_ok($$ insert into public.comunidades (organizacion_id, nombre) values (tests.u('org_a'), 'X') $$,
  '42501', null, 'A no escribe comunidades desde la web');
select throws_ok($$ update public.unidades set prorrateo = 0.1 $$, '42501', null, 'A no modifica prorrateos desde la web');
select throws_ok($$ insert into public.miembros_organizacion (organizacion_id, usuario_id, rol)
  values (tests.u('org_a'), tests.u('user_x'), 'owner') $$, '42501', null, 'A no se autoasigna miembros desde la web');

-- Equipo de la organización B.
select tests.como('user_b1');
select is((select count(*) from public.comunidades), 1::bigint, 'B ve solo su comunidad');
select is((select count(*) from public.unidades where organizacion_id = tests.u('org_a')), 0::bigint, 'B no ve unidades de A');
select is((select count(*) from public.miembros_organizacion), 1::bigint, 'B ve solo a su equipo');

-- Comité de A.
select tests.como('user_ca');
select is((select count(*) from public.comunidades), 1::bigint, 'el comité ve su comunidad y no la otra de A');
select is((select count(*) from public.unidades), 2::bigint, 'el comité ve todas las unidades de su comunidad');
select is((select count(*) from public.organizaciones), 0::bigint, 'el comité no ve organizaciones');
select is((select count(*) from public.miembros_organizacion), 0::bigint, 'el comité no ve al equipo');
select is((select count(*) from public.accesos_comunidad), 1::bigint, 'el comité ve solo su propio acceso');
select is((select count(*) from public.auditoria), 0::bigint, 'el comité no ve la auditoría');

-- Residente de la unidad A-101.
select tests.como('user_ra1');
select is((select count(*) from public.comunidades), 1::bigint, 'el residente ve su comunidad');
select is((select array_agg(codigo) from public.unidades), array['A-101'], 'el residente ve solo su unidad');
select is((select count(*) from public.accesos_comunidad), 1::bigint, 'el residente ve solo su acceso');
select is((select count(*) from public.miembros_organizacion), 0::bigint, 'el residente no ve al equipo');

-- Restricciones de la base (como la API).
select tests.como_api();
select throws_ok($$ insert into public.comunidades (organizacion_id, nombre, pct_reserva)
  values (tests.u('org_a'), 'Bajo mínimo', 0.04) $$, '23514', null, 'el recargo de reserva mínimo es 5 %');
select lives_ok($$ insert into public.comunidades (organizacion_id, nombre, pct_reserva)
  values (tests.u('org_a'), 'En el mínimo', 0.05) $$, 'el recargo de 5 % es válido');
select throws_ok($$ insert into public.unidades (organizacion_id, comunidad_id, codigo, prorrateo)
  values (tests.u('org_a'), tests.u('com_a'), 'A-999', 1.5) $$, '23514', null, 'el prorrateo no supera 1');
select throws_ok($$ insert into public.unidades (organizacion_id, comunidad_id, codigo, prorrateo)
  values (tests.u('org_a'), tests.u('com_a'), 'A-101', 0.1) $$, '23505', null, 'el código es único por comunidad');
select throws_ok($$ insert into public.unidades (organizacion_id, comunidad_id, codigo, prorrateo)
  values (tests.u('org_a'), tests.u('com_b'), 'X-1', 0.1) $$, '23503', null,
  'una unidad no puede mezclar la organización A con la comunidad de B');
select throws_ok($$ insert into public.accesos_comunidad (organizacion_id, comunidad_id, usuario_id, rol)
  values (tests.u('org_a'), tests.u('com_a'), tests.u('user_x'), 'residente') $$, '23514', null,
  'un residente exige unidad');
select throws_ok($$ insert into public.accesos_comunidad (organizacion_id, comunidad_id, usuario_id, rol, unidad_id)
  values (tests.u('org_a'), tests.u('com_a'), tests.u('user_x'), 'comite', tests.u('u_a101')) $$, '23514', null,
  'el comité no se ata a una unidad');
select throws_ok($$ insert into public.accesos_comunidad (organizacion_id, comunidad_id, usuario_id, rol, unidad_id)
  values (tests.u('org_a'), tests.u('com_a'), tests.u('user_x'), 'residente', tests.u('u_a2_1')) $$, '23503', null,
  'el residente solo se vincula a unidades de la misma comunidad');
select throws_ok($$ delete from public.unidades where id = tests.u('u_a101') $$, '23001', null, 'las unidades no se borran');
select throws_ok($$ delete from public.comunidades where id = tests.u('com_a2') $$, '23001', null, 'las comunidades no se borran');
select ok(public.prorrateos_suman_uno(tests.u('com_a')), 'los prorrateos de com_a suman 1');
update public.unidades set prorrateo = 0.4 where id = tests.u('u_a101');
select ok(not public.prorrateos_suman_uno(tests.u('com_a')), 'detecta prorrateos que no suman 1');

select * from finish();
rollback;
