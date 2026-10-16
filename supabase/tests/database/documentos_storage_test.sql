-- documentos y el bucket privado `documentos` (sección 15: Storage privado con rutas por organización).
begin;
select plan(22);
select tests.crear_escenario();

-- Tabla documentos.
select tests.como('user_a1');
select is((select count(*) from public.documentos), 2::bigint, 'A ve los documentos de su comunidad');
select is((select count(*) from public.documentos where organizacion_id = tests.u('org_b')), 0::bigint, 'A no ve documentos de B');
select lives_ok($$ insert into public.documentos (organizacion_id, comunidad_id, tipo, nombre, ruta_storage)
  values (tests.u('org_a'), tests.u('com_a'), 'acta', 'Acta', tests.u('org_a') || '/' || tests.u('com_a') || '/actas/1.pdf') $$,
  'A registra un documento en su comunidad');
select throws_ok($$ insert into public.documentos (organizacion_id, comunidad_id, tipo, nombre, ruta_storage)
  values (tests.u('org_b'), tests.u('com_b'), 'acta', 'Acta', tests.u('org_b') || '/' || tests.u('com_b') || '/actas/1.pdf') $$,
  '42501', null, 'A no registra documentos en B');
select throws_ok($$ insert into public.documentos (organizacion_id, comunidad_id, tipo, nombre, ruta_storage)
  values (tests.u('org_a'), tests.u('com_a'), 'acta', 'Acta', tests.u('org_b') || '/' || tests.u('com_b') || '/actas/2.pdf') $$,
  '23514', null, 'la ruta debe pertenecer a la organización y comunidad del documento');
select lives_ok($$ delete from public.documentos where id = tests.u('doc_b') $$, 'A intenta borrar un documento de B sin efecto');
select tests.como('user_ca');
select is((select count(*) from public.documentos), 3::bigint, 'el comité ve todos los documentos de su comunidad');
select throws_ok($$ insert into public.documentos (organizacion_id, comunidad_id, tipo, nombre, ruta_storage)
  values (tests.u('org_a'), tests.u('com_a'), 'acta', 'Acta', tests.u('org_a') || '/' || tests.u('com_a') || '/actas/3.pdf') $$,
  '42501', null, 'el comité no escribe documentos');
select tests.como('user_ra1');
select is((select array_agg(nombre) from public.documentos), array['Reglamento'], 'el residente ve solo los documentos visibles');
select tests.como('user_x');
select is((select count(*) from public.documentos), 0::bigint, 'un usuario sin vínculos no ve documentos');

-- Storage.
select tests.como_api();
select is((select public from storage.buckets where id = 'documentos'), false, 'el bucket documentos es privado');
select tests.como('user_a1');
select is((select count(*) from storage.objects where bucket_id = 'documentos'), 1::bigint, 'A ve solo sus archivos');
select lives_ok($$ insert into storage.objects (bucket_id, name, owner_id)
  values ('documentos', tests.u('org_a') || '/' || tests.u('com_a') || '/comprobantes/f1.pdf', tests.u('user_a1')::text) $$,
  'A sube un archivo a su comunidad');
select throws_ok($$ insert into storage.objects (bucket_id, name, owner_id)
  values ('documentos', tests.u('org_b') || '/' || tests.u('com_b') || '/comprobantes/intruso.pdf', tests.u('user_a1')::text) $$,
  '42501', null, 'A no sube archivos a la carpeta de B');
select throws_ok($$ insert into storage.objects (bucket_id, name, owner_id)
  values ('documentos', tests.u('org_a') || '/' || tests.u('com_b') || '/comprobantes/cruzado.pdf', tests.u('user_a1')::text) $$,
  '42501', null, 'A no sube a una comunidad ajena bajo su propia organización');
select throws_ok($$ insert into storage.objects (bucket_id, name, owner_id)
  values ('documentos', 'ruta-sin-uuid/x.pdf', tests.u('user_a1')::text) $$,
  '42501', null, 'una ruta que no empieza con la organización se rechaza');
select lives_ok($$ update storage.objects set name = 'robado.pdf' where name like tests.u('org_b') || '%' $$,
  'A intenta renombrar archivos de B sin efecto');
select tests.como('user_b1');
select is((select count(*) from storage.objects where bucket_id = 'documentos'), 1::bigint, 'B ve solo sus archivos y siguen intactos');
select tests.como('user_ca');
select is((select count(*) from storage.objects where bucket_id = 'documentos'), 2::bigint, 'el comité ve los archivos de su comunidad (el reglamento y el comprobante subido por A)');
select tests.como('user_cb');
select is((select count(*) from storage.objects where name like tests.u('org_a') || '%'), 0::bigint, 'el comité de B no ve archivos de A');
select tests.como('user_ra1');
select is((select count(*) from storage.objects), 0::bigint, 'el residente accede por URL firmada de la API, no directo a Storage');
select tests.como('user_x');
select is((select count(*) from storage.objects), 0::bigint, 'un usuario sin vínculos no ve archivos');

select * from finish();
rollback;
