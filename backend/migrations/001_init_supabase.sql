-- 001_init_supabase.sql
-- Sistema Inteligente de Revision de Codigo para Estudiantes
--
-- Ejecutar manualmente en el SQL Editor de Supabase (no se ejecuta desde el backend).
--
-- Contenido:
--   A.1 Tabla students (espejo de auth.users)
--   A.2 Trigger que sincroniza auth.users -> public.students
--   A.3 Tabla reviews
--   A.4 Indices basicos

create extension if not exists pgcrypto;

-- A.1 Tabla students (espejo de auth.users) --------------------------------
-- Se llena sola via el trigger de A.2 cuando exista signup (Supabase Auth).
-- El backend nunca inserta manualmente en esta tabla.

create table public.students (
  id uuid primary key references auth.users(id) on delete cascade,
  email text,
  created_at timestamp with time zone default now()
);

-- A.2 Trigger: auth.users -> public.students --------------------------------

create function public.handle_new_user()
returns trigger as $$
begin
  insert into public.students (id, email)
  values (new.id, new.email);
  return new;
end;
$$ language plpgsql security definer;

create trigger on_auth_user_created
  after insert on auth.users
  for each row execute procedure public.handle_new_user();

-- A.3 Tabla reviews ----------------------------------------------------------
-- student_id es nullable a proposito: mientras no haya login, queda NULL.
-- session_id agrupa revisiones anonimas de una misma sesion de uso.
-- response guarda el JSON completo devuelto por analizar_codigo como jsonb.

create table public.reviews (
  id uuid primary key default gen_random_uuid(),
  student_id uuid references public.students(id) on delete set null,
  session_id text,
  language text not null,
  exercise text,
  level text,
  review_type text,
  student_code text not null,
  response jsonb not null,
  created_at timestamp with time zone default now()
);

-- A.4 Indices basicos ---------------------------------------------------------

create index idx_reviews_student_id on public.reviews(student_id);
create index idx_reviews_session_id on public.reviews(session_id);
