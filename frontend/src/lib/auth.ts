// Auth client: accounts + the HttpOnly session cookie.
//
// Kept out of `api.ts` because these four calls are what AuthGate needs
// before any other endpoint is allowed to run, and because the cookie is the
// only state involved — nothing here stores a token in JS.

import { API_BASE } from "./api";

export interface AuthUser {
  id: number;
  email: string;
  display_name: string;
}

const WITH_COOKIE: RequestInit = { credentials: "include" };

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...WITH_COOKIE,
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    // FastAPI puts the human-readable reason in "detail"; a bare status code
    // would leave the login form with nothing to say.
    let detail = `${res.status}`;
    try {
      const payload = await res.json();
      if (typeof payload?.detail === "string") detail = payload.detail;
    } catch {
      /* non-JSON error body — keep the status */
    }
    throw new Error(detail);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const auth = {
  /** The current account, or null when the cookie is absent/expired. */
  me: async (): Promise<AuthUser | null> => {
    const res = await fetch(`${API_BASE}/auth/me`, WITH_COOKIE);
    if (res.status === 401) return null;
    if (!res.ok) throw new Error(`auth/me failed: ${res.status}`);
    return res.json() as Promise<AuthUser>;
  },

  login: (email: string, password: string) =>
    postJson<AuthUser>("/auth/login", { email, password }),

  register: (email: string, password: string, display_name = "") =>
    postJson<AuthUser>("/auth/register", { email, password, display_name }),

  logout: () => postJson<void>("/auth/logout", {}),
};
