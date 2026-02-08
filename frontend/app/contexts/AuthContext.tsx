"use client";

import React, { createContext, useContext, useState, useEffect, useCallback } from "react";
import {
  login as apiLogin,
  register as apiRegister,
  setTokens,
  loadTokens,
  clearTokens,
  getAccessToken,
  type AuthResponse,
} from "../lib/api";

interface UserInfo {
  id: string;
  email: string;
  full_name?: string;
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

  // Restore session on mount
  useEffect(() => {
    loadTokens();
    const saved = typeof window !== "undefined" ? localStorage.getItem("user") : null;
    if (saved && getAccessToken()) {
      try {
        setUser(JSON.parse(saved));
      } catch {
        clearTokens();
      }
    }
    setLoading(false);
  }, []);

  const handleAuth = useCallback((data: AuthResponse) => {
    setTokens(data.access_token, data.refresh_token);
    const userInfo: UserInfo = {
      id: data.user.id,
      email: data.user.email,
      full_name: data.user.full_name,
    };
    setUser(userInfo);
    if (typeof window !== "undefined") {
      localStorage.setItem("user", JSON.stringify(userInfo));
    }
  }, []);

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
