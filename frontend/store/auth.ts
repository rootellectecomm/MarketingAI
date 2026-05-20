"use client";

import { create } from "zustand";

const TOKEN_KEY = "rootellect_token";

function readStoredToken(): string | null {
  if (typeof window === "undefined") {
    return null;
  }
  return localStorage.getItem(TOKEN_KEY);
}

function persistToken(token: string | null) {
  if (typeof window === "undefined") {
    return;
  }
  if (token) {
    localStorage.setItem(TOKEN_KEY, token);
    document.cookie = `${TOKEN_KEY}=${token}; path=/; max-age=${60 * 60 * 24 * 7}; SameSite=Lax`;
  } else {
    localStorage.removeItem(TOKEN_KEY);
    document.cookie = `${TOKEN_KEY}=; path=/; max-age=0`;
  }
}

type AuthState = {
  token: string | null;
  hydrated: boolean;
  hydrate: () => void;
  setToken: (token: string) => void;
  logout: () => void;
};

export const useAuthStore = create<AuthState>((set) => ({
  token: null,
  hydrated: false,
  hydrate: () => {
    const token = readStoredToken();
    if (token) {
      persistToken(token);
    }
    set({ token, hydrated: true });
  },
  setToken: (token) => {
    persistToken(token);
    set({ token });
  },
  logout: () => {
    persistToken(null);
    set({ token: null });
  }
}));
