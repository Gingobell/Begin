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

// ── Fetch wrapper ─────────────────────────────────────────────────

async function apiFetch(path: string, opts: RequestInit = {}) {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(opts.headers as Record<string, string>),
  };
  if (_accessToken) {
    headers["Authorization"] = `Bearer ${_accessToken}`;
  }
  const res = await fetch(`${API_BASE}${path}`, { ...opts, headers });

  if (res.status === 401 && _refreshToken) {
    // Try refresh
    const refreshRes = await fetch(`${API_BASE}/api/v1/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: _refreshToken }),
    });
    if (refreshRes.ok) {
      const data = await refreshRes.json();
      setTokens(data.access_token, data.refresh_token);
      headers["Authorization"] = `Bearer ${data.access_token}`;
      return fetch(`${API_BASE}${path}`, { ...opts, headers });
    }
    clearTokens();
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
  const res = await apiFetch(`/api/v1/fortune/status?${params}`);
  if (!res.ok) throw new Error("Failed to check fortune status");
  return res.json();
}

export async function getDailyFortune(localDate?: string) {
  const params = new URLSearchParams();
  if (localDate) params.set("local_date", localDate);
  const res = await apiFetch(`/api/v1/fortune/daily?${params}`);
  if (!res.ok) throw new Error("Failed to get daily fortune");
  return res.json();
}

// ── Diary ─────────────────────────────────────────────────────────

export async function getDiaries() {
  const res = await apiFetch(`/api/v1/diaries`);
  if (!res.ok) throw new Error("Failed to get diaries");
  return res.json();
}

export async function createDiary(content: string, emotionTags?: string[]) {
  const res = await apiFetch(`/api/v1/diaries`, {
    method: "POST",
    body: JSON.stringify({ content, emotion_tags: emotionTags }),
  });
  if (!res.ok) throw new Error("Failed to create diary");
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
  const res = await apiFetch(`/api/v1/user/profile`);
  if (!res.ok) throw new Error("Failed to get user profile");
  return res.json();
}
