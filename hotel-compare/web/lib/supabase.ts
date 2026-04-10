import { createClient, SupabaseClient } from "@supabase/supabase-js";

let client: SupabaseClient | undefined;

function getClient(): SupabaseClient {
  if (!client) {
    client = createClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
    );
  }
  return client;
}

/** Lazy supabase client — avoids calling createClient at import time (build-safe for static export). */
export const supabase = new Proxy({} as SupabaseClient, {
  get(_, prop) {
    const c = getClient();
    const val = (c as any)[prop];
    return typeof val === "function" ? val.bind(c) : val;
  },
});
