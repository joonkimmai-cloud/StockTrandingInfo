import { createClient } from '@supabase/supabase-js';

const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL;
const SUPABASE_ANON_KEY = import.meta.env.VITE_SUPABASE_ANON_KEY;

export const supabase = createClient(SUPABASE_URL || '', SUPABASE_ANON_KEY || '');

export interface DailyReport {
  id?: string;
  market: 'US' | 'KR';
  date: string; // YYYY-MM-DD
  stocks: any[];
  summaries: any[];
  created_at?: string;
}

export const saveReport = async (report: DailyReport) => {
  const { data, error } = await supabase
    .from('daily_reports')
    .insert([report]);
    
  if (error) throw error;
  return data;
};

export const getLatestReport = async (market: 'US' | 'KR'): Promise<DailyReport | null> => {
  try {
    const { data, error } = await supabase
      .from('daily_reports')
      .select('*')
      .eq('market', market)
      .order('created_at', { ascending: false })
      .limit(1)
      .single();
      
    if (error) return null;
    return data;
  } catch (e) {
    return null;
  }
};
