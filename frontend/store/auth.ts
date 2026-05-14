"use client";

import { create } from "zustand";

type AuthState = {
  token: string | null;
  setToken: (token: string) => void;
  logout: () => void;
};

export const useAuthStore = create<AuthState>((set) => ({
  token: null,
  setToken: (token) => {
    localStorage.setItem("rootellect_token", token);
    set({ token });
  },
  logout: () => {
    localStorage.removeItem("rootellect_token");
    set({ token: null });
  }
}));

