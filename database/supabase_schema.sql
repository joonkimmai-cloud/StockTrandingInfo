CREATE TABLE IF NOT EXISTS public.companies (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    name TEXT NOT NULL,
    symbol TEXT NOT NULL UNIQUE,
    market TEXT NOT NULL, -- 'KR' or 'US'
    sector TEXT, -- 업종
    industry TEXT, -- 산업
    business_summary TEXT, -- 사업 요약
    issued_shares BIGINT, -- 발행주식 정보
    marcap BIGINT, -- 시가총액
    per NUMERIC, -- 주가수익비율
    pbr NUMERIC, -- 주가순자산비율
    revenue BIGINT, -- 매출 (Total Revenue)
    operating_margins NUMERIC, -- 영업이익률
    net_income BIGINT, -- 당기순이익
    website TEXT, -- 웹사이트
    city TEXT, -- 위치(도시)
    ceo TEXT, -- 대표자
    founded_date TEXT, -- 설립일
    listing_date TEXT, -- 상장일
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Create table for news articles
CREATE TABLE IF NOT EXISTS public.news_articles (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    company_id UUID REFERENCES public.companies(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    content TEXT, -- 기사 정보
    source_url TEXT,
    published_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Create table for subscribers (updated with is_active)
CREATE TABLE IF NOT EXISTS public.subscribers (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    is_active BOOLEAN DEFAULT true, -- 구독 활성화 여부
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- RLS Settings
ALTER TABLE public.companies ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.news_articles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.subscribers ENABLE ROW LEVEL SECURITY;

-- Allow service_role full access
CREATE POLICY "Allow service_role full access companies" ON public.companies FOR ALL USING (true);
CREATE POLICY "Allow service_role full access news" ON public.news_articles FOR ALL USING (true);
CREATE POLICY "Allow service_role full access subscribers" ON public.subscribers FOR ALL USING (true);

-- Allow public insert for subscribers (for the web form)
CREATE POLICY "Allow public insert subscribers" ON public.subscribers FOR INSERT WITH CHECK (true);
