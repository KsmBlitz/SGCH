begin;
select plan(3);
select tests.crear_escenario();
select is((select count(*) from public.cargos), 4::bigint, 'el escenario crea los cargos');
select is((select count(*) from public.auditoria where tabla = 'cargos'), 4::bigint, 'la auditoría registró los cargos');
select is((select estado from public.periodos where id = tests.u('per_a_ago')), 'emitido', 'el período de agosto quedó emitido');
select * from finish();
rollback;
