-- Analysis Reports and Investment Insights Table Migration
-- This script adds tables for market-wide analysis and individual stock insights

-- 1. Table for Market-wide Daily Analysis (Today's Outlook)
CREATE TABLE IF NOT EXISTS public.market_reports (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    report_date DATE DEFAULT CURRENT_DATE UNIQUE,
    market_summary TEXT NOT NULL, -- 전체 시장 요약
    investment_strategy TEXT NOT NULL, -- 오늘의 투자 방향 및 전략
    prediction TEXT, -- 증시 예측
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 2. Table for Individual Stock AI Analysis
CREATE TABLE IF NOT EXISTS public.stock_analysis (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    company_id UUID REFERENCES public.companies(id) ON DELETE CASCADE,
    report_id UUID REFERENCES public.market_reports(id) ON DELETE SET NULL,
    analysis_content TEXT NOT NULL,
    sentiment TEXT, -- Bullish / Bearish
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- RLS Settings
ALTER TABLE public.market_reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.stock_analysis ENABLE ROW LEVEL SECURITY;

-- Allow service_role full access
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname='Allow service_role full access market_reports') THEN
        CREATE POLICY "Allow service_role full access market_reports" ON public.market_reports FOR ALL USING (true);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname='Allow service_role full access stock_analysis') THEN
        CREATE POLICY "Allow service_role full access stock_analysis" ON public.stock_analysis FOR ALL USING (true);
    END IF;
END $$;

-- Comment for documentation
COMMENT ON TABLE public.market_reports IS '일일리포트 시장 분석 및 오늘의 투자 전략';
COMMENT ON TABLE public.stock_analysis IS '종목별 AI 상세 분석 결과';
