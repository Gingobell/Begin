"use client";

import React, { createContext, useContext, useState, useEffect, useCallback } from "react";
import {
  login as apiLogin,
  register as apiRegister,
  getUserProfile,
  setTokens,
  loadTokens,
  clearTokens,
  getAccessToken,
  refreshAccessToken,
  type AuthResponse,
} from "../lib/api";

interface UserInfo {
  id: string;
  email: string;
  full_name?: string;
  avatar_url?: string;
  birth_datetime?: string;
  gender?: string;
  fortune_categories?: string[];
  usageStats?: {
    registrationDate?: string;
    totalDays?: number;
    consecutiveCheckins?: number;
    totalDiaries?: number;
    monthlyDiaries?: number;
    totalConversations?: number;
    totalWords?: number;
    lastActiveDate?: string;
  };
}

interface AuthContextType {
  user: UserInfo | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, fullName?: string, birthday?: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<UserInfo | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchAndSetProfile = useCallback(async (base: UserInfo) => {
    try {
      const profile = await getUserProfile();
      const merged: UserInfo = { ...base, ...profile };
      setUser(merged);
      if (typeof window !== "undefined") {
        localStorage.setItem("user", JSON.stringify(merged));
      }
    } catch {
      // API 失败时保留基础信息
      setUser(base);
    }
  }, []);

  // Restore session on mount — proactively refresh token
  useEffect(() => {
    let cancelled = false;
    async function restore() {
      loadTokens();
      const saved = typeof window !== "undefined" ? localStorage.getItem("user") : null;
      if (saved && getAccessToken()) {
        try {
          const base = JSON.parse(saved) as UserInfo;
          setUser(base);
          const ok = await refreshAccessToken();
          if (!cancelled && ok) {
            fetchAndSetProfile(base);
          } else if (!cancelled) {
            setUser(null);
          }
        } catch {
          if (!cancelled) { clearTokens(); setUser(null); }
        }
      }
      if (!cancelled) setLoading(false);
    }
    restore();
    return () => { cancelled = true; };
  }, [fetchAndSetProfile]);

  const handleAuth = useCallback((data: AuthResponse) => {
    setTokens(data.access_token, data.refresh_token);
    const base: UserInfo = {
      id: data.user.id,
      email: data.user.email,
      full_name: data.user.full_name,
    };
    setUser(base);
    if (typeof window !== "undefined") {
      localStorage.setItem("user", JSON.stringify(base));
    }
    fetchAndSetProfile(base);
  }, [fetchAndSetProfile]);

  const loginFn = useCallback(
    async (email: string, password: string) => {
      const data = await apiLogin(email, password);
      handleAuth(data);
    },
    [handleAuth],
  );

  const registerFn = useCallback(
    async (email: string, password: string, fullName?: string, birthday?: string) => {
      const data = await apiRegister(email, password, fullName, birthday);
      if (data.access_token) {
        handleAuth(data);
      }
    },
    [handleAuth],
  );

  const logout = useCallback(() => {
    clearTokens();
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, login: loginFn, register: registerFn, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
