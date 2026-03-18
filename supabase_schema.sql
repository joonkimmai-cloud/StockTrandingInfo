-- Supabase SQL Schema
-- Run this in your Supabase SQL Editor

CREATE TABLE IF NOT EXISTS public.daily_reports (
  id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
  market text NOT NULL,
  date date DEFAULT CURRENT_DATE,
  stocks jsonb NOT NULL,
  summaries jsonb NOT NULL,
  created_at timestamp with time zone DEFAULT now()
);

-- Optional: Add index for faster lookup
CREATE INDEX IF NOT EXISTS idx_market_created ON daily_reports (market, created_at DESC);

-- Allow anonymous access (if using anon key)
ALTER TABLE public.daily_reports ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Public read" ON public.daily_reports FOR SELECT USING (true);
CREATE POLICY "Service insert" ON public.daily_reports FOR INSERT WITH CHECK (true);
