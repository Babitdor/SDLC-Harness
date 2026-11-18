"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { UNAUTHORIZED_EVENT } from "../lib/api";
import { auth, type AuthUser } from "../lib/auth";
import LoginForm from "./LoginForm";

export interface AuthSession {
  user: AuthUser;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthSession | null>(null);

/**
 * The signed-in account, inside <AuthGate>.
 *
 * Returns null outside a gate so components stay renderable in isolation —
 * AppNav's own test renders it with no provider.
 */
export function useAuthSession(): AuthSession | null {
  return useContext(AuthContext);
}

/**
 * Page-level gate: children render only for a valid session.
 *
 * Inline rather than a /login route on purpose — no router or proxy surface,
 * and no redirect flash on load. A deep-linkable login page would need
 * middleware; this app has one screen, so it does not.
 */
export default function AuthGate({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    let cancelled = false;
    auth
      .me()
      .then((current) => {
        if (!cancelled) setUser(current);
      })
      .catch(() => {
        // Backend unreachable or returned something unexpected: treat it like
        // a dead session rather than stranding the user on a blank screen.
        if (!cancelled) setUser(null);
      })
      .finally(() => {
        if (!cancelled) setChecking(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // Any 401 anywhere (api.ts dispatches auth:unauthorized) re-opens the form.
  // A session that expires mid-chat would otherwise leave every panel failing
  // silently.
  useEffect(() => {
    const onUnauthorized = () => setUser(null);
    window.addEventListener(UNAUTHORIZED_EVENT, onUnauthorized);
    return () => window.removeEventListener(UNAUTHORIZED_EVENT, onUnauthorized);
  }, []);

  const signOut = useCallback(async () => {
    try {
      await auth.logout();
    } finally {
      setUser(null);
    }
  }, []);

  if (checking) {
    return (
      <div className="flex h-dvh items-center justify-center bg-base-950">
        <span className="label-mono text-base-500">VERIFYING SESSION…</span>
      </div>
    );
  }

  if (!user) return <LoginForm onAuthenticated={setUser} />;

  return (
    <AuthContext.Provider value={{ user, signOut }}>{children}</AuthContext.Provider>
  );
}
