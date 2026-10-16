-- auditoria: solo inserción, con usuario y valores anteriores y nuevos (sección 8: cierre y auditoría).
begin;
select plan(14);
select tests.crear_escenario();

select tests.como_api();
select throws_ok($$ update public.auditoria set tabla = 'x' $$, '23001', null, 'la auditoría no se actualiza');
select throws_ok($$ delete from public.auditoria $$, '23001', null, 'la auditoría no se borra');
select throws_ok($$ truncate public.auditoria $$, '23001', null, 'la auditoría no se trunca');

-- Un cambio de dinero registra quién, cuándo y qué valores.
select set_config('app.usuario_id', tests.u('user_a1')::text, true);
update public.gastos set monto_clp = 250000 where id = tests.u('gasto_a_sep');
select is((select accion from public.auditoria where registro_id = tests.u('gasto_a_sep') order by id desc limit 1),
  'update', 'se audita la actualización del gasto');
select is((select usuario_id from public.auditoria where registro_id = tests.u('gasto_a_sep') order by id desc limit 1),
  tests.u('user_a1'), 'la auditoría guarda el usuario que declara la API');
select is((select (anterior ->> 'monto_clp')::int from public.auditoria where registro_id = tests.u('gasto_a_sep') order by id desc limit 1),
  200000, 'guarda el valor anterior');
select is((select (nuevo ->> 'monto_clp')::int from public.auditoria where registro_id = tests.u('gasto_a_sep') order by id desc limit 1),
  250000, 'guarda el valor nuevo');
select is((select organizacion_id from public.auditoria where registro_id = tests.u('gasto_a_sep') order by id desc limit 1),
  tests.u('org_a'), 'la auditoría pertenece a la organización del registro');

-- Cada tabla con efecto económico está auditada.
select is(
  (select count(*) from unnest(array['comunidades', 'unidades', 'grupo_prorrateo_unidades', 'periodos', 'gastos', 'cargos',
                                      'pagos', 'aplicaciones_pago', 'movimientos_cartola', 'fondo_reserva_movimientos',
                                      'rendiciones']) t
   where not exists (select 1 from information_schema.triggers g
                     where g.event_object_schema = 'public' and g.event_object_table = t
                       and g.action_statement like '%registrar_auditoria%')),
  0::bigint, 'toda tabla con efecto económico tiene su trigger de auditoría');
select is(
  (select count(*) from unnest(array['organizaciones', 'comunidades', 'unidades', 'periodos', 'gastos', 'cargos', 'pagos',
                                      'aplicaciones_pago', 'movimientos_cartola', 'fondo_reserva_movimientos',
                                      'rendiciones']) t
   where not exists (select 1 from information_schema.triggers g
                     where g.event_object_schema = 'public' and g.event_object_table = t
                       and g.action_statement like '%impedir_borrado%')),
  0::bigint, 'toda tabla con efecto económico bloquea el borrado');

-- Los roles de la web no escriben ni leen la auditoría ajena.
select tests.como('user_a1');
select throws_ok($$ insert into public.auditoria (organizacion_id, tabla, registro_id, accion, nuevo)
  values (tests.u('org_a'), 'x', gen_random_uuid(), 'insert', '{}') $$, '42501', null, 'la web no inserta auditoría');
select is((select count(*) from public.auditoria where organizacion_id = tests.u('org_b')), 0::bigint, 'A no ve la auditoría de B');
select tests.como('user_ra1');
select is((select count(*) from public.auditoria), 0::bigint, 'el residente no ve la auditoría');
select tests.como('user_ca');
select is((select count(*) from public.auditoria), 0::bigint, 'el comité no ve la auditoría');

select * from finish();
rollback;
