/**
 * API client for FortuneDiary backend.
 * All REST calls go through here with auth token injection.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

// ── Token management ──────────────────────────────────────────────

let _accessToken: string | null = null;
let _refreshToken: string | null = null;

export function setTokens(access: string, refresh: string) {
  _accessToken = access;
  _refreshToken = refresh;
  if (typeof window !== "undefined") {
    localStorage.setItem("access_token", access);
    localStorage.setItem("refresh_token", refresh);
  }
}

export function loadTokens() {
  if (typeof window !== "undefined") {
    _accessToken = localStorage.getItem("access_token");
    _refreshToken = localStorage.getItem("refresh_token");
  }
}

export function clearTokens() {
  _accessToken = null;
  _refreshToken = null;
  if (typeof window !== "undefined") {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    localStorage.removeItem("user");
  }
}

export function getAccessToken() {
  return _accessToken;
}

export async function refreshAccessToken(): Promise<boolean> {
  return deduplicatedRefresh();
}

// ── Cache layer ──────────────────────────────────────────────────

interface CacheEntry { data: unknown; ts: number }
const _cache = new Map<string, CacheEntry>();
const DEFAULT_TTL = 5 * 60 * 1000; // 5 min

function cacheKey(path: string, headers?: Record<string, string>) {
  const lang = headers?.["Accept-Language"] || "";
  return lang ? `${path}|${lang}` : path;
}

function getCached(key: string, ttl: number): unknown | null {
  const e = _cache.get(key);
  if (e && Date.now() - e.ts < ttl) return e.data;
  if (e) _cache.delete(key);
  return null;
}

function setCache(key: string, data: unknown) {
  _cache.set(key, { data, ts: Date.now() });
}

/** Invalidate cache entries whose key starts with the given prefix */
export function invalidateCache(prefix: string) {
  Array.from(_cache.keys()).forEach(k => {
    if (k.startsWith(prefix)) _cache.delete(k);
  });
}

// ── Fetch wrapper ─────────────────────────────────────────────────

let _refreshPromise: Promise<boolean> | null = null;

/** Deduplicated refresh: concurrent 401s share a single refresh call */
async function deduplicatedRefresh(): Promise<boolean> {
  if (_refreshPromise) return _refreshPromise;
  _refreshPromise = (async () => {
    if (!_refreshToken) return false;
    try {
      const res = await fetch(`${API_BASE}/api/v1/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: _refreshToken }),
      });
      if (res.ok) {
        const data = await res.json();
        setTokens(data.access_token, data.refresh_token);
        return true;
      }
    } catch {}
    clearTokens();
    return false;
  })().finally(() => { _refreshPromise = null; });
  return _refreshPromise;
}

function getStoredLocale(): string {
  if (typeof window !== "undefined") {
    return localStorage.getItem("begin-locale") || "en-US";
  }
  return "en-US";
}

async function apiFetch(path: string, opts: RequestInit = {}) {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    "Accept-Language": getStoredLocale(),
    ...(opts.headers as Record<string, string>),
  };
  if (_accessToken) {
    headers["Authorization"] = `Bearer ${_accessToken}`;
  }
  const res = await fetch(`${API_BASE}${path}`, { ...opts, headers });

  if (res.status === 401 && _refreshToken) {
    const ok = await deduplicatedRefresh();
    if (ok) {
      headers["Authorization"] = `Bearer ${_accessToken}`;
      return fetch(`${API_BASE}${path}`, { ...opts, headers });
    }
    throw new Error("Session expired");
  }

  return res;
}

// ── Auth ───────────────────────────────────────────────────────────

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  user: { id: string; email: string; full_name?: string };
}

export async function login(email: string, password: string): Promise<AuthResponse> {
  const res = await fetch(`${API_BASE}/api/v1/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Login failed" }));
    throw new Error(err.detail || "Login failed");
  }
  return res.json();
}

export async function register(
  email: string,
  password: string,
  fullName?: string,
  birthday?: string,
): Promise<AuthResponse> {
  const res = await fetch(`${API_BASE}/api/v1/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password, full_name: fullName, birthday }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Register failed" }));
    throw new Error(err.detail || "Register failed");
  }
  return res.json();
}

// ── Fortune ───────────────────────────────────────────────────────

export async function getFortuneStatus(localDate?: string) {
  const params = new URLSearchParams();
  if (localDate) params.set("local_date", localDate);
  const path = `/api/v1/fortune/status?${params}`;
  const key = cacheKey(path);
  const hit = getCached(key, DEFAULT_TTL);
  if (hit) return hit;
  const res = await apiFetch(path);
  if (!res.ok) throw new Error("Failed to check fortune status");
  const data = await res.json();
  setCache(key, data);
  return data;
}

export async function getDailyFortune(localDate?: string, language?: string, forceRegenerate?: boolean) {
  const params = new URLSearchParams();
  if (localDate) params.set("local_date", localDate);
  if (forceRegenerate) params.set("force_regenerate", "true");
  const headers: Record<string, string> = {};
  if (language) headers["Accept-Language"] = language;
  const path = `/api/v1/fortune/daily?${params}`;
  // Skip cache when force regenerating
  if (!forceRegenerate) {
    const key = cacheKey(path, headers);
    const hit = getCached(key, DEFAULT_TTL);
    if (hit) return hit;
  }
  const res = await apiFetch(path, { headers });
  if (!res.ok) throw new Error("Failed to get daily fortune");
  const data = await res.json();
  setCache(cacheKey(path, headers), data);
  return data;
}

// ── Diary ─────────────────────────────────────────────────────────

export async function getDiaries() {
  const path = `/api/v1/diaries`;
  const key = cacheKey(path);
  const hit = getCached(key, DEFAULT_TTL);
  if (hit) return hit;
  const res = await apiFetch(path);
  if (!res.ok) throw new Error("Failed to get diaries");
  const data = await res.json();
  setCache(key, data);
  return data;
}

export async function createDiary(content: string, emotionTags?: string[]) {
  const res = await apiFetch(`/api/v1/diaries`, {
    method: "POST",
    body: JSON.stringify({ content, emotion_tags: emotionTags }),
  });
  if (!res.ok) throw new Error("Failed to create diary");
  invalidateCache("/api/v1/diaries");
  return res.json();
}

export async function searchDiaries(keyword: string, limit = 20) {
  const params = new URLSearchParams({ keyword, limit: String(limit) });
  const res = await apiFetch(`/api/v1/diaries/search?${params}`);
  if (!res.ok) throw new Error("Failed to search diaries");
  return res.json();
}

// ── User ──────────────────────────────────────────────────────────

export async function getUserProfile() {
  const path = `/api/v1/user/profile`;
  const key = cacheKey(path);
  const hit = getCached(key, DEFAULT_TTL);
  if (hit) return hit;
  const res = await apiFetch(path);
  if (!res.ok) throw new Error("Failed to get user profile");
  const data = await res.json();
  setCache(key, data);
  return data;
}
