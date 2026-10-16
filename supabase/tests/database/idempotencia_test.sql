-- idempotencia: tabla exclusiva de la API.
begin;
select plan(7);
select tests.crear_escenario();

select tests.como('user_a1');
select throws_ok($$ select * from public.idempotencia $$, '42501', null, 'el equipo no lee la idempotencia');
select throws_ok($$ insert into public.idempotencia (organizacion_id, clave, operacion, huella)
  values (tests.u('org_a'), 'k', 'cerrar', 'h') $$, '42501', null, 'el equipo no escribe la idempotencia');
select tests.como_anonimo();
select throws_ok($$ select * from public.idempotencia $$, '42501', null, 'anon no lee la idempotencia');

select tests.como_api();
insert into public.idempotencia (organizacion_id, clave, operacion, huella)
values (tests.u('org_a'), 'clave-1', 'cerrar_periodo', 'huella');
select throws_ok($$ insert into public.idempotencia (organizacion_id, clave, operacion, huella)
  values (tests.u('org_a'), 'clave-1', 'cerrar_periodo', 'huella') $$, '23505', null,
  'una clave se usa una vez por organización');
select lives_ok($$ insert into public.idempotencia (organizacion_id, clave, operacion, huella)
  values (tests.u('org_b'), 'clave-1', 'cerrar_periodo', 'huella') $$,
  'otra organización puede usar la misma clave');
select throws_ok($$ insert into public.idempotencia (organizacion_id, clave, operacion, huella, codigo_http)
  values (tests.u('org_a'), 'clave-2', 'x', 'h', 200) $$, '23514', null, 'respuesta y código van juntos');
select is((select relrowsecurity from pg_class where oid = 'public.idempotencia'::regclass), true, 'tiene RLS');

select * from finish();
rollback;
