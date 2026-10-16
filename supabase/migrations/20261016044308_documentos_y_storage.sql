-- Documentos de la comunidad y Storage privado (secciones 10 y 15).
-- Rutas: {organizacion_id}/{comunidad_id}/{carpeta}/{archivo}. Los residentes acceden solo con URLs
-- firmadas de corta duración que emite la API; las políticas cubren al equipo y al comité.

create table public.documentos (
  id                  uuid primary key default gen_random_uuid(),
  organizacion_id     uuid not null,
  comunidad_id        uuid not null,
  tipo                text not null check (tipo in ('reglamento', 'acta', 'contrato', 'otro')),
  nombre              text not null check (length(trim(nombre)) > 0),
  ruta_storage        text not null,
  visible_residentes  boolean not null default false,
  creado_en           timestamptz not null default now(),
  creado_por          uuid references auth.users (id),
  foreign key (comunidad_id, organizacion_id) references public.comunidades (id, organizacion_id),
  check (ruta_storage like organizacion_id::text || '/' || comunidad_id::text || '/%'),
  unique (ruta_storage)
);

create index documentos_comunidad_idx on public.documentos (comunidad_id);

alter table public.documentos enable row level security;

grant select, insert, update, delete on public.documentos to authenticated;

create policy "documentos: equipo lee" on public.documentos
  for select to authenticated using (public.es_miembro_org(organizacion_id));
create policy "documentos: equipo inserta" on public.documentos
  for insert to authenticated with check (public.es_miembro_org(organizacion_id));
create policy "documentos: equipo actualiza" on public.documentos
  for update to authenticated
  using (public.es_miembro_org(organizacion_id))
  with check (public.es_miembro_org(organizacion_id));
create policy "documentos: equipo borra" on public.documentos
  for delete to authenticated using (public.es_miembro_org(organizacion_id));
create policy "documentos: comite lee" on public.documentos
  for select to authenticated
  using (public.tiene_acceso_comunidad(comunidad_id, array['comite']));
create policy "documentos: residentes leen los visibles" on public.documentos
  for select to authenticated
  using (visible_residentes and public.tiene_acceso_comunidad(comunidad_id, array['residente']));

-- ---------------------------------------------------------------------------
-- Storage
-- ---------------------------------------------------------------------------

-- Convierte un tramo de la ruta en uuid sin fallar si no lo es.
create function public.uuid_o_nulo(p_texto text)
returns uuid
language sql
immutable
set search_path = ''
as $$
  select case
    when p_texto ~* '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$' then p_texto::uuid
  end;
$$;

grant execute on function public.uuid_o_nulo(text) to authenticated, service_role;

insert into storage.buckets (id, name, public)
values ('documentos', 'documentos', false)
on conflict (id) do nothing;

create policy "documentos storage: equipo lee"
  on storage.objects for select to authenticated
  using (
    bucket_id = 'documentos'
    and public.es_miembro_org(public.uuid_o_nulo((storage.foldername(name))[1]))
  );

create policy "documentos storage: equipo sube a sus comunidades"
  on storage.objects for insert to authenticated
  with check (
    bucket_id = 'documentos'
    and public.es_miembro_org(public.uuid_o_nulo((storage.foldername(name))[1]))
    and exists (
      select 1 from public.comunidades c
      where c.id = public.uuid_o_nulo((storage.foldername(name))[2])
        and c.organizacion_id = public.uuid_o_nulo((storage.foldername(name))[1])
    )
  );

create policy "documentos storage: equipo actualiza"
  on storage.objects for update to authenticated
  using (
    bucket_id = 'documentos'
    and public.es_miembro_org(public.uuid_o_nulo((storage.foldername(name))[1]))
  )
  with check (
    bucket_id = 'documentos'
    and public.es_miembro_org(public.uuid_o_nulo((storage.foldername(name))[1]))
  );

create policy "documentos storage: equipo borra"
  on storage.objects for delete to authenticated
  using (
    bucket_id = 'documentos'
    and public.es_miembro_org(public.uuid_o_nulo((storage.foldername(name))[1]))
  );

create policy "documentos storage: comite lee su comunidad"
  on storage.objects for select to authenticated
  using (
    bucket_id = 'documentos'
    and public.tiene_acceso_comunidad(public.uuid_o_nulo((storage.foldername(name))[2]), array['comite'])
  );
