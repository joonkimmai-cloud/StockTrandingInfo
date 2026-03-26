-- Execution Logs and Batch Summary Table Migration
-- This script adds tables to track background batch processes and detailed logs

-- 1. Table for Detailed Execution Logs
CREATE TABLE IF NOT EXISTS public.execution_logs (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    step_name TEXT NOT NULL,
    status TEXT NOT NULL,
    log_message TEXT,
    error_detail TEXT,
    execution_time INTERVAL,
    log_content TEXT, -- 상세 실행 내용 (stdout 등)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 2. Table for Batch Execution Summary (The Latest State)
CREATE TABLE IF NOT EXISTS public.batch_summary (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    last_run_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    last_status TEXT NOT NULL,
    success_count INTEGER DEFAULT 0,
    fail_count INTEGER DEFAULT 0,
    summary_message TEXT,
    log_content TEXT, -- 전체 실행 로그 요약
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- RLS Settings
ALTER TABLE public.execution_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.batch_summary ENABLE ROW LEVEL SECURITY;

-- Allow service_role full access
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname='Allow service_role full access execution_logs') THEN
        CREATE POLICY "Allow service_role full access execution_logs" ON public.execution_logs FOR ALL USING (true);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname='Allow service_role full access batch_summary') THEN
        CREATE POLICY "Allow service_role full access batch_summary" ON public.batch_summary FOR ALL USING (true);
    END IF;
END $$;

-- Comment for documentation
COMMENT ON TABLE public.execution_logs IS '배치 프로세스의 단계별 상세 실행 로그';
COMMENT ON TABLE public.batch_summary IS '최근 배치 실행 상태 요약 정보';
