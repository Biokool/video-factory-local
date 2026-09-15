-- =============================================================================
--  ESQUEMA RAG — QUIROMANCIA TERAPÉUTICA
-- =============================================================================
--  Base de conocimiento vectorial para la fábrica local de video IA.
--
--  Modela un manual de quiromancia como:
--    documentos  →  (1:N) secciones  →  (1:N) fragmentos (con embedding)
--
--  El propósito es:
--    1. Rastrear un tema (ej. "línea de la vida") a lo largo de TODO el libro,
--       en orden cronológico, usando las `secciones` como índice estructural.
--    2. Recuperar fragmentos semánticamente relevantes por similitud coseno
--       (embeddings de nomic-embed-text, 768 dimensiones).
--
--  Los metadatos capturan la taxonomía propia de la quiromancia:
--    linea_vida, linea_corazon, linea_cabeza, monte_venus, monte_jupiter,
--    dedo_pulgar, etc. — para poder filtrar por categoría.
--
--  Cómo aplicar:
--    psql "$SUPABASE_DB_URL" -f 001_rag.sql
--  (o pegarlo en Supabase → SQL Editor)
-- =============================================================================

-- 1. Extensión pgvector -------------------------------------------------------
create extension if not exists vector;

-- 2. Documentos fuente -------------------------------------------------------
--    Un documento = un manual/PDF ingerido (ej. "Manual_Quiromancia_2026.pdf").
create table if not exists public.documentos (
  id uuid primary key default gen_random_uuid(),
  source_path text not null,                 -- ruta del archivo origen
  source_name text not null,                 -- nombre del archivo
  categoria text,                            -- p.ej. 'quiromancia', 'quiromagia'
  titulo text,                               -- título del manual
  autor text,                                -- autor (p.ej. 'Prof. Francisco Rodríguez')
  contenido text not null,                   -- texto íntegro extraído
  checksum_sha256 text not null,             -- integridad / dedupe
  metadatos jsonb not null default '{}'::jsonb,
  creado_en timestamptz not null default now()
);

-- 3. Secciones (índice estructural del libro) ---------------------------------
--    Conserva la jerarquía y el ORDEN del manual (crucial para el storytelling
--    cronológico). Ej.: '4. La Línea de la Vida', '4.1 Interpretación...'.
create table if not exists public.secciones (
  id bigserial primary key,
  documento_id uuid not null references public.documentos(id) on delete cascade,
  numero text not null,                      -- '4', '4.1', '4.2.1'
  titulo text not null,                      -- 'La Línea de la Vida'
  orden integer not null,                    -- posición en el libro
  contenido text,                            -- texto de la sección
  creado_en timestamptz not null default now()
);

create index if not exists secciones_documento_orden_idx
  on public.secciones(documento_id, orden);

-- 4. Fragmentos con embedding -------------------------------------------------
--    Cada fragmento es un chunk semántico (~450-700 tokens) con su vector de
--    768 dimensiones. `categoria` guarda la taxonomía de quiromancia.
create table if not exists public.fragmentos (
  id bigserial primary key,
  documento_id uuid not null references public.documentos(id) on delete cascade,
  seccion_id bigint references public.secciones(id) on delete set null,
  chunk_index integer not null,              -- orden del chunk en el documento
  contenido text not null,
  token_count integer,
  categoria text,                            -- linea_vida, monte_venus, ...
  metadatos jsonb not null default '{}'::jsonb,
  embedding vector(768) not null,
  creado_en timestamptz not null default now()
);

create index if not exists fragmentos_documento_idx
  on public.fragmentos(documento_id);

create index if not exists fragmentos_categoria_idx
  on public.fragmentos(categoria);

-- El índice vectorial (HNSW) se crea una vez validado el volumen de datos.
-- Para pocos fragmentos la búsqueda secuencial es suficiente.
-- create index if not exists fragmentos_embedding_hnsw_idx
--   on public.fragmentos using hnsw (embedding vector_cosine_ops);

-- 5. Búsqueda semántica (RPC) ------------------------------------------------
--    Devuelve los fragmentos más similares a la consulta (coseno), con filtro
--    opcional por categoría de quiromancia.
create or replace function public.buscar_fragmentos(
  consulta_embedding vector(768),
  max_resultados int default 6,
  filtro_categoria text default null
)
returns table (
  id bigint,
  documento_id uuid,
  seccion_id bigint,
  contenido text,
  categoria text,
  metadatos jsonb,
  similitud float
)
language sql
stable
as $$
  select
    f.id,
    f.documento_id,
    f.seccion_id,
    f.contenido,
    f.categoria,
    f.metadatos,
    (1 - (f.embedding <=> consulta_embedding))::float as similitud
  from public.fragmentos f
  where filtro_categoria is null
     or f.categoria = filtro_categoria
  order by f.embedding <=> consulta_embedding
  limit least(greatest(max_resultados, 1), 20);
$$;

-- 6. Vista de lectura cronológica ---------------------------------------------
--    Reconstruye el "hilo" de un tema a lo largo del libro: fragmentos
--    ordenados por documento → sección → chunk (útil para storytelling).
create or replace view public.vista_cronologica as
select
  d.id as documento_id,
  d.titulo as documento_titulo,
  s.numero as seccion_numero,
  s.titulo as seccion_titulo,
  s.orden as seccion_orden,
  f.chunk_index,
  f.categoria,
  f.contenido
from public.fragmentos f
join public.documentos d on d.id = f.documento_id
left join public.secciones s on s.id = f.seccion_id
order by d.creado_en, s.orden, f.chunk_index;
