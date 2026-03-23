-- Existing table cleanup/extension migration
-- This script adds new financial fields to the existing companies table

-- Add marcap (Market Cap) column
DO $$ 
BEGIN 
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='companies' AND column_name='marcap') THEN
        ALTER TABLE public.companies ADD COLUMN marcap BIGINT;
    END IF;
END $$;

-- Add per (Price to Earnings Ratio) column
DO $$ 
BEGIN 
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='companies' AND column_name='per') THEN
        ALTER TABLE public.companies ADD COLUMN per NUMERIC;
    END IF;
END $$;

-- Add pbr (Price to Book Ratio) column
DO $$ 
BEGIN 
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='companies' AND column_name='pbr') THEN
        ALTER TABLE public.companies ADD COLUMN pbr NUMERIC;
    END IF;
END $$;

-- Comment for documentation
COMMENT ON COLUMN public.companies.marcap IS '시가총액';
COMMENT ON COLUMN public.companies.per IS '주가수익비율';
COMMENT ON COLUMN public.companies.pbr IS '주가순자산비율';
