import { create } from "zustand";
import client from "../api/client";

interface AuthState {
  token: string | null;
  username: string | null;
  login: (username: string, password: string) => Promise<void>;
  register: (username: string, password: string, email?: string) => Promise<void>;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  token: localStorage.getItem("token"),
  username: localStorage.getItem("username"),

  login: async (username, password) => {
    const response = await client.post("/auth/login", { username, password });
    const token = response.data.access_token as string;
    localStorage.setItem("token", token);
    localStorage.setItem("username", username);
    set({ token, username });
  },

  register: async (username, password, email) => {
    const response = await client.post("/auth/register", { username, password, email });
    const token = response.data.access_token as string;
    localStorage.setItem("token", token);
    localStorage.setItem("username", username);
    set({ token, username });
  },

  logout: () => {
    localStorage.removeItem("token");
    localStorage.removeItem("username");
    set({ token: null, username: null });
  },
}));
