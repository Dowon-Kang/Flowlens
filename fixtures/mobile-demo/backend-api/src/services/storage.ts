import { createClient } from '@supabase/supabase-js';
export async function saveMeasurement(value: unknown) {
  const supabase = createClient(process.env.SUPABASE_URL!, process.env.SUPABASE_KEY!);
  return supabase.from('measurements').insert(value);
}
