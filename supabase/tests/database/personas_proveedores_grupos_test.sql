-- personas, unidad_personas, proveedores, grupos_prorrateo y grupo_prorrateo_unidades.
begin;
select plan(29);
select tests.crear_escenario();

-- Equipo A: control total sobre personas, vínculos y proveedores de su organización.
select tests.como('user_a1');
select is((select count(*) from public.personas), 2::bigint, 'A ve sus personas');
select is((select count(*) from public.personas where organizacion_id = tests.u('org_b')), 0::bigint, 'A no ve personas de B');
select is((select count(*) from public.unidad_personas where organizacion_id = tests.u('org_b')), 0::bigint, 'A no ve vínculos de B');
select is((select count(*) from public.proveedores where organizacion_id = tests.u('org_b')), 0::bigint, 'A no ve proveedores de B');
select is((select count(*) from public.grupos_prorrateo where organizacion_id = tests.u('org_b')), 0::bigint, 'A no ve grupos de B');
select is((select count(*) from public.grupo_prorrateo_unidades where organizacion_id = tests.u('org_b')), 0::bigint, 'A no ve miembros de grupos de B');
select lives_ok($$ insert into public.personas (organizacion_id, nombre) values (tests.u('org_a'), 'Nueva') $$,
  'A crea personas en su organización');
select throws_ok($$ insert into public.personas (organizacion_id, nombre) values (tests.u('org_b'), 'Intrusa') $$,
  '42501', null, 'A no crea personas en B');
select throws_ok($$ insert into public.proveedores (organizacion_id, comunidad_id, nombre)
  values (tests.u('org_b'), tests.u('com_b'), 'Intruso') $$, '42501', null, 'A no crea proveedores en B');
select throws_ok($$ insert into public.unidad_personas (organizacion_id, comunidad_id, unidad_id, persona_id, rol, desde)
  values (tests.u('org_a'), tests.u('com_b'), tests.u('u_b201'), tests.u('persona_a'), 'residente', current_date) $$,
  '23503', null, 'A no vincula personas propias con unidades de B');
select lives_ok($$ update public.personas set nombre = 'Hackeada' where id = tests.u('persona_b') $$,
  'A intenta actualizar una persona de B sin error pero sin efecto');
select lives_ok($$ delete from public.proveedores where id = tests.u('prov_b') $$,
  'A intenta borrar un proveedor de B sin error pero sin efecto');
select throws_ok($$ insert into public.grupos_prorrateo (organizacion_id, comunidad_id, nombre)
  values (tests.u('org_a'), tests.u('com_a'), 'Torre C') $$, '42501', null,
  'A no escribe grupos de prorrateo desde la web (alteran montos)');

-- Equipo B.
select tests.como('user_b1');
select is((select count(*) from public.personas), 1::bigint, 'B ve solo sus personas');
select is((select count(*) from public.proveedores), 1::bigint, 'B ve solo sus proveedores');

-- Comité de A: ve proveedores y grupos, no los datos personales.
select tests.como('user_ca');
select is((select count(*) from public.personas), 0::bigint, 'el comité no ve personas');
select is((select count(*) from public.unidad_personas), 0::bigint, 'el comité no ve vínculos');
select is((select count(*) from public.proveedores), 1::bigint, 'el comité ve los proveedores de su comunidad');
select is((select count(*) from public.grupos_prorrateo), 1::bigint, 'el comité ve los grupos de su comunidad');
select throws_ok($$ insert into public.proveedores (organizacion_id, comunidad_id, nombre)
  values (tests.u('org_a'), tests.u('com_a'), 'Comité') $$, '42501', null, 'el comité no escribe proveedores');

-- Residente de A-101: solo las personas de su unidad.
select tests.como('user_ra1');
select is((select array_agg(nombre) from public.personas), array['Persona Ficticia A'], 'el residente ve a las personas de su unidad');
select is((select count(*) from public.unidad_personas), 1::bigint, 'el residente ve los vínculos de su unidad');
select is((select count(*) from public.proveedores), 0::bigint, 'el residente no ve proveedores');

-- Reglas de la base (como la API).
select tests.como_api();
select is((select nombre from public.personas where id = tests.u('persona_b')), 'Persona Ficticia B',
  'la persona de B quedó intacta');
select is((select count(*) from public.proveedores where id = tests.u('prov_b')), 1::bigint,
  'el proveedor de B sigue existiendo');
select throws_ok($$ insert into public.personas (organizacion_id, nombre, rut)
  values (tests.u('org_a'), 'RUT mal formado', '12.345.678-5') $$, '23514', null, 'el RUT se guarda normalizado');
select ok(public.grupo_prorrateo_suma_uno(tests.u('grupo_a')), 'el grupo A suma 1');
insert into public.grupo_prorrateo_unidades (organizacion_id, comunidad_id, grupo_id, unidad_id, prorrateo)
values (tests.u('org_a'), tests.u('com_a'), tests.u('grupo_a'), tests.u('u_a102'), 0.5);
select ok(not public.grupo_prorrateo_suma_uno(tests.u('grupo_a')), 'detecta un grupo que no suma 1');
delete from public.grupo_prorrateo_unidades where grupo_id = tests.u('grupo_a') and unidad_id = tests.u('u_a102');
select is((select accion from public.auditoria where tabla = 'grupo_prorrateo_unidades' order by id desc limit 1),
  'delete', 'el borrado de un miembro de grupo queda en la auditoría');

select * from finish();
rollback;
