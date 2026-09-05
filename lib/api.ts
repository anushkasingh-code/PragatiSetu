export const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

export type ApiResult<T> =
  | { ok: true; data: T }
  | { ok: false; error: string; status?: number };

async function extractErrorMessage(res: Response): Promise<string> {
  const fallback = `${res.status} ${res.statusText}`.trim();
  try {
    const text = await res.text();
    if (!text || !text.trim()) return fallback;
    try {
      const body = JSON.parse(text);
      if (typeof body.detail === 'string') return body.detail;
      if (body.detail && typeof body.detail.message === 'string') return body.detail.message;
      if (Array.isArray(body.detail) && body.detail[0]?.msg) return body.detail[0].msg;
      if (typeof body.message === 'string') return body.message;
      if (typeof body.error === 'string') return body.error;
      return JSON.stringify(body);
    } catch {
      return text.trim() || fallback;
    }
  } catch {
    return fallback;
  }
}

export async function apiFetch<T = unknown>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, init);
  if (!res.ok) {
    const errorMsg = await extractErrorMessage(res);
    const err = new Error(errorMsg);
    (err as any).status = res.status;
    throw err;
  }
  const text = await res.text();
  if (!text || !text.trim()) {
    return {} as T;
  }
  try {
    return JSON.parse(text) as T;
  } catch {
    return text as unknown as T;
  }
}

/** Non-throwing fetch with timeout — use in pipelines where graceful fallback is required. */
export async function apiFetchSafe<T = unknown>(path: string, init?: RequestInit, timeoutMs = 8000): Promise<ApiResult<T>> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(`${API_BASE}${path}`, {
      ...init,
      signal: init?.signal ?? controller.signal,
    });
    clearTimeout(timer);
    if (!res.ok) {
      const error = await extractErrorMessage(res);
      return { ok: false, error, status: res.status };
    }
    const text = await res.text();
    if (!text || !text.trim()) {
      return { ok: true, data: {} as T };
    }
    try {
      const data = JSON.parse(text) as T;
      return { ok: true, data };
    } catch {
      return { ok: true, data: text as unknown as T };
    }
  } catch (err) {
    clearTimeout(timer);
    return {
      ok: false,
      error: err instanceof Error ? (err.name === 'AbortError' ? 'Request timed out' : err.message) : 'Network error',
    };
  }
}
