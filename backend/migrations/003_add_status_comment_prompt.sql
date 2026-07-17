-- 003_add_status_comment_prompt.sql
-- Sistema Inteligente de Revision de Codigo para Estudiantes
--
-- Ejecutar manualmente en el SQL Editor de Supabase (no se ejecuta desde el backend).
--
-- Agrega revision humana (RF-08: aceptar/descartar/comentar) y trazabilidad del
-- prompt real enviado al LLM (RF-09/RNF-05). status default 'pending' se aplica
-- retroactivamente a las revisiones existentes - no hace falta backfill especial.

alter table public.reviews
  add column status text not null default 'pending'
    check (status in ('pending', 'accepted', 'discarded')),
  add column student_comment text,
  add column prompt_sent text;
