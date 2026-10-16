-- Datos ficticios de desarrollo local. Nunca datos reales de personas (regla 8 de CLAUDE.md).
-- Misma comunidad que apps/api/tests/comunidad_ficticia.py: "Mirador de Curauma", 16 departamentos.
do $$
declare
  v_org  uuid := gen_random_uuid();
  v_admin uuid := gen_random_uuid();
  v_com  uuid := gen_random_uuid();
  v_per  uuid := gen_random_uuid();
begin
  insert into auth.users (id, aud, role, email)
  values (v_admin, 'authenticated', 'authenticated', 'admin@demo.sgch.test');

  insert into public.organizaciones (id, nombre, plan, prueba_hasta)
  values (v_org, 'Administradora Demo', 'prueba', date '2026-12-31');

  insert into public.miembros_organizacion (organizacion_id, usuario_id, rol)
  values (v_org, v_admin, 'owner');

  insert into public.comunidades (id, organizacion_id, nombre, rut, direccion, comuna, pct_reserva, tasa_interes_mora)
  values (v_com, v_org, 'Mirador de Curauma', '76000000-0', 'Av. Ficticia 1234', 'Valparaíso', 0.05, 0.01);

  insert into public.unidades (organizacion_id, comunidad_id, codigo, prorrateo)
  select v_org, v_com, codigo, prorrateo
  from (values
    ('A-101', 0.04943056), ('A-102', 0.06192661), ('A-201', 0.04943056), ('A-202', 0.06192661),
    ('A-301', 0.04943056), ('A-302', 0.06192661), ('A-401', 0.08296425), ('A-402', 0.08296425),
    ('B-101', 0.04943056), ('B-102', 0.06192661), ('B-201', 0.04943056), ('B-202', 0.06192660),
    ('B-301', 0.04943056), ('B-302', 0.06192660), ('B-401', 0.08296425), ('B-402', 0.08296425)
  ) as u (codigo, prorrateo);

  if not public.prorrateos_suman_uno(v_com) then
    raise exception 'El seed de prorrateos debe sumar exactamente 1.';
  end if;

  insert into public.periodos (id, organizacion_id, comunidad_id, mes)
  values (v_per, v_org, v_com, date '2026-10-01');

  insert into public.gastos (organizacion_id, comunidad_id, periodo_id, tipo, categoria, descripcion, monto_clp, fecha)
  values
    (v_org, v_com, v_per, 'ordinario', 'administracion', 'Honorarios del administrador', 280000, date '2026-10-05'),
    (v_org, v_com, v_per, 'ordinario', 'administracion', 'Conserjería', 1150000, date '2026-10-05'),
    (v_org, v_com, v_per, 'ordinario', 'mantencion', 'Mantención de ascensores (2 torres)', 190000, date '2026-10-08'),
    (v_org, v_com, v_per, 'ordinario', 'mantencion', 'Aseo de espacios comunes', 220000, date '2026-10-08'),
    (v_org, v_com, v_per, 'ordinario', 'uso_consumo', 'Electricidad de espacios comunes', 87430, date '2026-10-10'),
    (v_org, v_com, v_per, 'ordinario', 'uso_consumo', 'Agua de espacios comunes', 41290, date '2026-10-10');
end $$;
