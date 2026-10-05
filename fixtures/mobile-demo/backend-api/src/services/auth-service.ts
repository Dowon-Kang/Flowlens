import { createClient } from '@supabase/supabase-js';
export async function signIn(input: unknown) {
  const supabase = createClient(process.env.SUPABASE_URL!, process.env.SUPABASE_KEY!);
  return supabase.auth.signInWithOtp(input as any);
}
