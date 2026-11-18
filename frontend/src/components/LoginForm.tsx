"use client";

import { useState } from "react";
import { auth, type AuthUser } from "../lib/auth";

type Mode = "login" | "register";

interface Props {
  onAuthenticated: (user: AuthUser) => void;
}

// Mirrors MIN_PASSWORD_LENGTH in the backend. Length only — the server is the
// authority, this is just so the field can say so before a round trip.
const MIN_PASSWORD_LENGTH = 10;

export default function LoginForm({ onAuthenticated }: Props) {
  const [mode, setMode] = useState<Mode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (busy) return;
    setBusy(true);
    setError(null);
    try {
      const user =
        mode === "login"
          ? await auth.login(email, password)
          : await auth.register(email, password);
      onAuthenticated(user);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setBusy(false);
    }
  };

  const switchMode = (next: Mode) => {
    setMode(next);
    setError(null);
  };

  return (
    <div className="flex h-dvh items-center justify-center bg-base-950 px-4">
      <div className="w-full max-w-sm border border-base-700 bg-base-900/60">
        <div className="border-b border-base-700 px-5 py-4">
          <div className="label-mono text-blue-400/80">SDLC / V0.2</div>
          <h1 className="dossier-title mt-1 text-[20px] text-base-100">Harness</h1>
          <p className="mt-2 text-[12px] leading-relaxed text-base-400">
            {mode === "login"
              ? "Sign in to reach your conversations and their sandboxes."
              : "Create an account. Chats are private to the account that made them."}
          </p>
        </div>

        <form onSubmit={submit} className="flex flex-col gap-3 px-5 py-4">
          <label className="block">
            <span className="label-mono text-base-500">Email</span>
            <input
              type="email"
              name="email"
              autoComplete="username"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="mt-1 w-full px-3 py-2 bg-base-950 border border-base-600 text-base-100 text-[13px] focus:outline-none focus:border-blue-500/60"
            />
          </label>

          <label className="block">
            <span className="label-mono text-base-500">Password</span>
            <input
              type="password"
              name="password"
              autoComplete={mode === "login" ? "current-password" : "new-password"}
              required
              minLength={mode === "register" ? MIN_PASSWORD_LENGTH : undefined}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="mt-1 w-full px-3 py-2 bg-base-950 border border-base-600 text-base-100 text-[13px] focus:outline-none focus:border-blue-500/60"
            />
            {mode === "register" && (
              <span className="mt-1 block text-[11px] text-base-500">
                At least {MIN_PASSWORD_LENGTH} characters. A passphrase is fine.
              </span>
            )}
          </label>

          {error && (
            <p
              role="alert"
              className="border border-danger/40 px-3 py-2 text-[12px] text-danger-400"
            >
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={busy}
            className="mt-1 px-3 py-2 border border-blue-400/60 bg-blue-400/10 text-blue-300 label-mono hover:bg-blue-400/20 transition-colors disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
          >
            {busy ? "WORKING…" : mode === "login" ? "SIGN IN" : "CREATE ACCOUNT"}
          </button>

          <button
            type="button"
            onClick={() => switchMode(mode === "login" ? "register" : "login")}
            className="label-mono text-base-500 hover:text-base-200 transition-colors cursor-pointer"
          >
            {mode === "login" ? "NO ACCOUNT? REGISTER" : "HAVE AN ACCOUNT? SIGN IN"}
          </button>
        </form>
      </div>
    </div>
  );
}
