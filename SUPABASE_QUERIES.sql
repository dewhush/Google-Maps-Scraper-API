-- Run this in your Supabase SQL Editor:

CREATE TABLE IF NOT EXISTS scrape_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    query TEXT NOT NULL,
    location TEXT,
    results_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now(),
    leads JSONB DEFAULT '[]'
);

-- Indices for performance
CREATE INDEX IF NOT EXISTS idx_scrape_history_user_id ON scrape_history(user_id);
CREATE INDEX IF NOT EXISTS idx_scrape_history_created_at ON scrape_history(created_at DESC);
