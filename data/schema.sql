"""
Supabase schema migration for LocalLens.

Run this SQL in the Supabase SQL editor to create the required tables
and the pgvector similarity search function.
"""

-- Enable pgvector extension if not already enabled
CREATE EXTENSION IF NOT EXISTS vector;

-- ── Articles Table ───────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS articles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    url TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    body TEXT NOT NULL DEFAULT '',
    source TEXT NOT NULL,
    source_level TEXT NOT NULL CHECK (source_level IN ('global', 'national', 'state', 'local')),
    locale TEXT NOT NULL DEFAULT 'san-diego-ca',
    published_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    embedding VECTOR(1024)
);

CREATE INDEX IF NOT EXISTS idx_articles_source_level ON articles(source_level);
CREATE INDEX IF NOT EXISTS idx_articles_locale ON articles(locale);
CREATE INDEX IF NOT EXISTS idx_articles_published_at ON articles(published_at DESC);

CREATE INDEX IF NOT EXISTS idx_articles_embedding ON articles
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);


-- ── Connections Table ────────────────────────────────────────────────────
-- Note: local_article_id is NULLABLE because in the "scoop" architecture,
-- impact is generated directly from global headlines + locale profile,
-- not by matching to existing local articles.

CREATE TABLE IF NOT EXISTS connections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    global_article_id UUID NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
    local_article_id UUID REFERENCES articles(id) ON DELETE SET NULL,  -- nullable: optional matching
    locale TEXT NOT NULL DEFAULT 'san-diego-ca',
    confidence TEXT NOT NULL CHECK (confidence IN ('low', 'medium', 'high')),
    mechanism_text TEXT NOT NULL,
    card_title TEXT NOT NULL,
    card_body TEXT NOT NULL,
    topics TEXT[] NOT NULL DEFAULT '{}',
    is_sensitive BOOLEAN NOT NULL DEFAULT FALSE,
    scoop_angle TEXT NOT NULL DEFAULT '',       -- what makes this analysis original
    neighborhoods_affected TEXT NOT NULL DEFAULT '',  -- specific neighborhoods/groups
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    cached_until TIMESTAMPTZ NOT NULL DEFAULT now() + interval '6 hours'
);

CREATE INDEX IF NOT EXISTS idx_connections_locale ON connections(locale);
CREATE INDEX IF NOT EXISTS idx_connections_cached_until ON connections(cached_until);
CREATE INDEX IF NOT EXISTS idx_connections_confidence ON connections(confidence);
CREATE INDEX IF NOT EXISTS idx_connections_topics ON connections USING GIN(topics);


-- ── Locale Profiles Table ───────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS locale_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    locale_slug TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    metro_code TEXT NOT NULL DEFAULT '',
    context_json JSONB NOT NULL DEFAULT '{}',  -- rich JSON with demographics, economy, geography, infrastructure, military
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_locale_profiles_slug ON locale_profiles(locale_slug);


-- ── pgvector Similarity Search Function ─────────────────────────────────

CREATE OR REPLACE FUNCTION match_articles(
    query_embedding VECTOR(1024),
    match_threshold FLOAT,
    match_count INT,
    filter_locale TEXT,
    filter_level TEXT
)
RETURNS TABLE (
    id UUID,
    url TEXT,
    title TEXT,
    body TEXT,
    source TEXT,
    source_level TEXT,
    locale TEXT,
    published_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        a.id,
        a.url,
        a.title,
        a.body,
        a.source,
        a.source_level,
        a.locale,
        a.published_at,
        a.created_at,
        1 - (a.embedding <=> query_embedding) AS similarity
    FROM articles a
    WHERE
        a.embedding IS NOT NULL
        AND a.locale = filter_locale
        AND a.source_level = filter_level
        AND 1 - (a.embedding <=> query_embedding) > match_threshold
    ORDER BY a.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;
