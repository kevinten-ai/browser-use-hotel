// hotel-compare/page-agent-version/supabase-bridge.js
/**
 * Supabase REST Bridge for Chrome Extension Service Worker
 * =========================================================
 * Lightweight fetch-based Supabase client — no SDK dependency.
 *
 * Reads SUPABASE_URL and SUPABASE_ANON_KEY from chrome.storage.local
 * with empty-string fallbacks (user must configure via storage).
 *
 * Exported functions:
 *   supabaseInsert(table, data)   — POST a row, returns inserted row
 *   supabaseFetch(table, filters) — GET rows with optional query filters
 *   supabaseUpdate(table, id, data) — PATCH a row by uuid/id
 *   supabaseUploadScreenshot(path, base64Data) — Upload to Storage bucket
 *   getSupabaseConfig() — Returns { url, key } from storage
 */

// ---------------------------------------------------------------------------
// Config helpers
// ---------------------------------------------------------------------------

/**
 * Load Supabase credentials from chrome.storage.local.
 * Falls back to empty strings — the caller should handle missing config.
 */
export async function getSupabaseConfig() {
  return new Promise((resolve) => {
    chrome.storage.local.get(['SUPABASE_URL', 'SUPABASE_ANON_KEY'], (items) => {
      resolve({
        url: items.SUPABASE_URL || '',
        key: items.SUPABASE_ANON_KEY || '',
      });
    });
  });
}

/**
 * Returns true if Supabase is configured (both URL and key are non-empty).
 */
export async function isSupabaseConfigured() {
  const { url, key } = await getSupabaseConfig();
  return Boolean(url && key);
}

/**
 * Build standard headers for Supabase REST API calls.
 */
function buildHeaders(key, extra = {}) {
  return {
    apikey: key,
    Authorization: `Bearer ${key}`,
    'Content-Type': 'application/json',
    Prefer: 'return=representation',
    ...extra,
  };
}

// ---------------------------------------------------------------------------
// REST helpers
// ---------------------------------------------------------------------------

/**
 * INSERT a row into `table`.
 * @param {string} table  — Supabase table name
 * @param {object} data   — Row payload
 * @returns {object} The inserted row (Prefer: return=representation)
 */
export async function supabaseInsert(table, data) {
  const { url, key } = await getSupabaseConfig();
  if (!url || !key) throw new Error('Supabase not configured');

  const res = await fetch(`${url}/rest/v1/${table}`, {
    method: 'POST',
    headers: buildHeaders(key),
    body: JSON.stringify(data),
  });

  if (!res.ok) {
    const body = await res.text();
    throw new Error(`Supabase INSERT ${table} failed (${res.status}): ${body}`);
  }

  const rows = await res.json();
  // Supabase returns an array; we inserted one row.
  return Array.isArray(rows) ? rows[0] : rows;
}

/**
 * SELECT rows from `table` with optional query-string filters.
 * @param {string} table   — Supabase table name
 * @param {object} filters — Key/value pairs appended as query params.
 *   Special keys:
 *     select  → columns to return (default '*')
 *     order   → order clause, e.g. 'created_at.desc'
 *     limit   → max rows
 *   Other keys are treated as PostgREST filters:
 *     { status: 'eq.pending', engine: 'in.(page-agent,dual)' }
 * @returns {Array} Array of matching rows
 */
export async function supabaseFetch(table, filters = {}) {
  const { url, key } = await getSupabaseConfig();
  if (!url || !key) throw new Error('Supabase not configured');

  const params = new URLSearchParams();
  params.set('select', filters.select || '*');
  if (filters.order) params.set('order', filters.order);
  if (filters.limit) params.set('limit', String(filters.limit));

  // Remaining keys are PostgREST column filters
  for (const [k, v] of Object.entries(filters)) {
    if (['select', 'order', 'limit'].includes(k)) continue;
    params.set(k, v);
  }

  const res = await fetch(`${url}/rest/v1/${table}?${params}`, {
    method: 'GET',
    headers: buildHeaders(key),
  });

  if (!res.ok) {
    const body = await res.text();
    throw new Error(`Supabase SELECT ${table} failed (${res.status}): ${body}`);
  }

  return res.json();
}

/**
 * UPDATE a row in `table` by its primary key.
 * @param {string} table        — Supabase table name
 * @param {string|number} id    — Row id (uuid for tasks, bigint for others)
 * @param {object} data         — Fields to patch
 * @param {string} idColumn     — Name of the PK column (default 'id')
 * @returns {object} The updated row
 */
export async function supabaseUpdate(table, id, data, idColumn = 'id') {
  const { url, key } = await getSupabaseConfig();
  if (!url || !key) throw new Error('Supabase not configured');

  const res = await fetch(`${url}/rest/v1/${table}?${idColumn}=eq.${id}`, {
    method: 'PATCH',
    headers: buildHeaders(key),
    body: JSON.stringify(data),
  });

  if (!res.ok) {
    const body = await res.text();
    throw new Error(`Supabase UPDATE ${table} failed (${res.status}): ${body}`);
  }

  const rows = await res.json();
  return Array.isArray(rows) ? rows[0] : rows;
}

/**
 * Upload a screenshot to Supabase Storage (screenshots bucket).
 * Uses the REST Storage API with base64-decoded binary upload.
 * @param {string} path       — Object path inside the bucket, e.g. 'task-uuid/step-1.png'
 * @param {string} base64Data — Base64-encoded PNG data (without data:image/png;base64, prefix)
 * @returns {object} { publicUrl } — The public URL of the uploaded file
 */
export async function supabaseUploadScreenshot(path, base64Data) {
  const { url, key } = await getSupabaseConfig();
  if (!url || !key) throw new Error('Supabase not configured');

  // Convert base64 to Uint8Array for binary upload
  const binaryString = atob(base64Data);
  const bytes = new Uint8Array(binaryString.length);
  for (let i = 0; i < binaryString.length; i++) {
    bytes[i] = binaryString.charCodeAt(i);
  }

  const res = await fetch(`${url}/storage/v1/object/screenshots/${path}`, {
    method: 'POST',
    headers: {
      apikey: key,
      Authorization: `Bearer ${key}`,
      'Content-Type': 'image/png',
      'x-upsert': 'true',
    },
    body: bytes,
  });

  if (!res.ok) {
    const body = await res.text();
    throw new Error(`Supabase Storage upload failed (${res.status}): ${body}`);
  }

  // Return public URL
  const publicUrl = `${url}/storage/v1/object/public/screenshots/${path}`;
  return { publicUrl };
}
