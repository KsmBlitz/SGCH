-- Base de SGCH: privilegios mínimos por defecto y funciones genéricas de integridad.
-- Sección 10 del documento maestro y .claude/rules/supabase.md.

-- Nada se concede por defecto a los roles de la web. Cada migración otorga explícitamente
-- lo que corresponde (por lo general solo SELECT; la escritura de dinero la hace la API).
alter default privileges for role postgres in schema public
  revoke all on tables from anon, authenticated;
alter default privileges for role postgres in schema public
  revoke all on sequences from anon, authenticated;
-- Postgres concede EXECUTE a PUBLIC en toda función nueva (eso solo se quita sin acotar el
-- esquema) y Supabase lo concede además a anon y authenticated en `public`.
alter default privileges for role postgres revoke execute on functions from public;
alter default privileges for role postgres in schema public
  revoke execute on functions from anon, authenticated;

-- Usuario que origina un cambio. En la web viene del JWT (auth.uid()). La API, que se conecta
-- con un rol que omite RLS, lo declara por transacción con
-- `select set_config('app.usuario_id', '<uuid>', true)`.
create function public.usuario_actual()
returns uuid
language sql
stable
set search_path = ''
as $$
  select coalesce(auth.uid(), nullif(current_setting('app.usuario_id', true), '')::uuid);
$$;

-- Bloquea el borrado físico de filas con efecto económico, incluso para el rol de la API.
create function public.impedir_borrado()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  raise exception 'No se pueden borrar filas de %: se anulan con motivo.', tg_table_name
    using errcode = 'restrict_violation';
end;
$$;

-- En tablas inmutables solo pueden cambiar las columnas de anulación, y una anulación no se revierte.
create function public.impedir_edicion_salvo_anulacion()
returns trigger
language plpgsql
set search_path = ''
as $$
declare
  v_columnas constant text[] := array['anulado_en', 'anulado_por', 'motivo'];
begin
  if (to_jsonb(old) - v_columnas) is distinct from (to_jsonb(new) - v_columnas) then
    raise exception 'Las filas de % no se editan: solo se pueden anular.', tg_table_name
      using errcode = 'restrict_violation';
  end if;
  if old.anulado_en is not null
     and (new.anulado_en, new.anulado_por, new.motivo)
         is distinct from (old.anulado_en, old.anulado_por, old.motivo) then
    raise exception 'La fila de % ya está anulada y no se puede modificar.', tg_table_name
      using errcode = 'restrict_violation';
  end if;
  return new;
end;
$$;

grant execute on function public.usuario_actual() to authenticated, service_role;
