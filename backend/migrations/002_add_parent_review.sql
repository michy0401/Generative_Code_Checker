-- 002_add_parent_review.sql
-- Sistema Inteligente de Revision de Codigo para Estudiantes
--
-- Ejecutar manualmente en el SQL Editor de Supabase (no se ejecuta desde el backend).
--
-- Agrega la relacion entre una revision y la revision anterior que la origino
-- (regeneracion). parent_review_id es NULL para revisiones originales.

alter table public.reviews
  add column parent_review_id uuid references public.reviews(id) on delete set null;

create index idx_reviews_parent_review_id on public.reviews(parent_review_id);
