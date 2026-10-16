-- Invariantes globales: RLS en todas las tablas, ninguna concesión a anon y escritura de dinero
-- reservada a la API (regla 4 de CLAUDE.md y sección 10 del documento maestro).
begin;
select plan(30);

select is(
  (select count(*) from pg_class c join pg_namespace n on n.oid = c.relnamespace
   where n.nspname = 'public' and c.relkind in ('r', 'p') and not c.relrowsecurity),
  0::bigint, 'toda tabla de public tiene RLS habilitado');

select is(
  (select count(*) from information_schema.tables t
   where t.table_schema = 'public' and t.table_type = 'BASE TABLE'
     and not exists (select 1 from information_schema.columns c
                     where c.table_schema = 'public' and c.table_name = t.table_name
                       and c.column_name = 'organizacion_id')
     and t.table_name <> 'organizaciones'),
  0::bigint, 'toda tabla de negocio lleva organizacion_id');

select is(
  (select relrowsecurity from pg_class where oid = 'storage.objects'::regclass),
  true, 'storage.objects tiene RLS habilitado');

select is(
  (select count(*) from information_schema.role_table_grants
   where table_schema = 'public' and grantee in ('anon', 'public')),
  0::bigint, 'anon no tiene privilegios sobre las tablas');

select is(
  (select count(*) from pg_proc p join pg_namespace n on n.oid = p.pronamespace
   where n.nspname = 'public' and has_function_privilege('anon', p.oid, 'execute')),
  0::bigint, 'anon no puede ejecutar funciones de public');

-- La web nunca escribe dinero: solo SELECT en tablas con efecto económico.
select ok(
  not has_table_privilege('authenticated', 'public.' || t, 'insert')
  and not has_table_privilege('authenticated', 'public.' || t, 'update')
  and not has_table_privilege('authenticated', 'public.' || t, 'delete'),
  t || ': authenticated solo lee')
from unnest(array[
  'organizaciones', 'miembros_organizacion', 'comunidades', 'unidades', 'accesos_comunidad', 'auditoria',
  'grupos_prorrateo', 'grupo_prorrateo_unidades', 'periodos', 'gastos', 'cargos', 'pagos',
  'aplicaciones_pago', 'movimientos_cartola', 'fondo_reserva_movimientos', 'rendiciones'
]) as t;

-- Un anónimo no lee nada.
select tests.crear_escenario();
select tests.como_anonimo();
select throws_ok($$ select * from public.comunidades $$, '42501', null, 'anon no lee comunidades');
select throws_ok($$ select * from public.cargos $$, '42501', null, 'anon no lee cargos');
select throws_ok($$ select public.es_miembro_org(gen_random_uuid()) $$, '42501', null,
  'anon no ejecuta las funciones de RLS');

-- Un usuario autenticado sin vínculos no ve nada.
select tests.como('user_x');
select is((select count(*) from public.comunidades), 0::bigint, 'sin vínculos no ve comunidades');
select is((select count(*) from public.cargos), 0::bigint, 'sin vínculos no ve cargos');
select is((select count(*) from public.pagos), 0::bigint, 'sin vínculos no ve pagos');
select is((select count(*) from public.personas), 0::bigint, 'sin vínculos no ve personas');
select is((select count(*) from public.auditoria), 0::bigint, 'sin vínculos no ve la auditoría');
select is((select count(*) from storage.objects), 0::bigint, 'sin vínculos no ve archivos');

select * from finish();
rollback;
