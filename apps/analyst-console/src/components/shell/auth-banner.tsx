import { useState } from "react";

import { Lock, Slash } from "lucide-react";

type AuthBannerProps = {
  busy: boolean;
  error: string | null;
  info: string | null;
  recoveryMode: boolean;
  onSignIn: (payload: { email: string; password: string }) => Promise<void> | void;
  onForgotPassword: (email: string) => Promise<void> | void;
  onUpdatePassword: (payload: { password: string }) => Promise<void> | void;
};

export function AuthBanner({
  busy,
  error,
  info,
  recoveryMode,
  onSignIn,
  onForgotPassword,
  onUpdatePassword,
}: AuthBannerProps) {
  const [signInEmail, setSignInEmail] = useState("");
  const [signInPassword, setSignInPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  return (
    <section className="flex min-h-0 flex-1 items-center justify-center bg-[var(--console-bg)] px-6 py-8">
      <div className="flex w-full max-w-[520px] flex-col items-center">
        <div className="flex flex-col items-center text-center">
          <div className="flex h-14 w-14 items-center justify-center rounded-lg border border-[var(--console-line)] bg-[var(--console-panel)] text-base font-semibold tracking-[0.18em] text-[var(--console-ink)]">
            SN
          </div>
          <div className="mt-5 flex items-center gap-1.5 text-[11px] uppercase tracking-[0.16em] text-[var(--console-muted)]">
            <span className="font-semibold text-[var(--console-ink)]">Sentinel</span>
            <Slash
              aria-hidden="true"
              className="h-3 w-3 shrink-0 text-[var(--console-muted)]"
            />
            <span>Analyst Console</span>
          </div>
          <h1 className="mt-3 text-3xl font-semibold text-[var(--console-ink)]">
            Restricted workspace
          </h1>
          <p className="mt-3 max-w-[44ch] text-sm leading-6 text-[var(--console-muted)]">
            Sign in with an invited account to open the review, release, audit,
            registry, and notification workspace.
          </p>
        </div>

        <div className="mt-8 w-full rounded-xl border border-[var(--console-line)] bg-[var(--console-panel)] p-6 shadow-[0_18px_44px_rgba(2,8,23,0.22)]">
          <div className="flex items-center gap-2 text-sm font-medium text-[var(--console-ink)]">
            <Lock
              aria-hidden="true"
              className="h-4 w-4 text-[var(--console-accent)]"
            />
            {recoveryMode ? "Reset password" : "Sign in"}
          </div>
          <p className="mt-2 text-sm text-[var(--console-muted)]">
            {recoveryMode
              ? "Set a new password for your invited analyst-console account."
              : "Invited analysts, RAs, and admins only."}
          </p>

          {error ? (
            <div className="mt-4 rounded-md border border-[var(--console-danger)]/40 bg-[var(--console-danger)]/10 px-3 py-3 text-sm text-[var(--console-danger)]">
              {error}
            </div>
          ) : null}

          {info ? (
            <div className="mt-4 rounded-md border border-[var(--console-accent)]/30 bg-[var(--console-panel-2)] px-3 py-3 text-sm text-[var(--console-ink)]">
              {info}
            </div>
          ) : null}

          {recoveryMode ? (
            <form
              className="mt-6 grid gap-3"
              onSubmit={(event) => {
                event.preventDefault();
                if (newPassword !== confirmPassword) {
                  return;
                }
                void onUpdatePassword({ password: newPassword });
              }}
            >
              <input
                className="rounded-md border border-[var(--console-line)] bg-[var(--console-bg)] px-3 py-2 text-sm text-[var(--console-ink)] outline-none"
                onChange={(event) => setNewPassword(event.target.value)}
                placeholder="New password"
                type="password"
                value={newPassword}
              />
              <input
                className="rounded-md border border-[var(--console-line)] bg-[var(--console-bg)] px-3 py-2 text-sm text-[var(--console-ink)] outline-none"
                onChange={(event) => setConfirmPassword(event.target.value)}
                placeholder="Confirm new password"
                type="password"
                value={confirmPassword}
              />
              {confirmPassword && newPassword !== confirmPassword ? (
                <p className="text-sm text-[var(--console-danger)]">
                  Passwords must match.
                </p>
              ) : null}
              <button
                className="rounded-md border border-[var(--console-accent)] bg-[var(--console-panel-2)] px-3 py-2 text-sm font-medium text-[var(--console-ink)] disabled:cursor-not-allowed disabled:opacity-60"
                disabled={busy || !newPassword || newPassword !== confirmPassword}
                type="submit"
              >
                {busy ? "Working…" : "Update password"}
              </button>
            </form>
          ) : (
            <form
              className="mt-6 grid gap-3"
              onSubmit={(event) => {
                event.preventDefault();
                void onSignIn({ email: signInEmail, password: signInPassword });
              }}
            >
              <input
                className="rounded-md border border-[var(--console-line)] bg-[var(--console-bg)] px-3 py-2 text-sm text-[var(--console-ink)] outline-none"
                onChange={(event) => setSignInEmail(event.target.value)}
                placeholder="Email"
                type="email"
                value={signInEmail}
              />
              <input
                className="rounded-md border border-[var(--console-line)] bg-[var(--console-bg)] px-3 py-2 text-sm text-[var(--console-ink)] outline-none"
                onChange={(event) => setSignInPassword(event.target.value)}
                placeholder="Password"
                type="password"
                value={signInPassword}
              />
              <button
                className="rounded-md border border-[var(--console-accent)] bg-[var(--console-panel-2)] px-3 py-2 text-sm font-medium text-[var(--console-ink)] disabled:cursor-not-allowed disabled:opacity-60"
                disabled={busy}
                type="submit"
              >
                {busy ? "Working…" : "Sign in"}
              </button>
            </form>
          )}

          <div className="mt-4 flex items-center justify-between gap-3 text-sm">
            {!recoveryMode ? (
              <button
                className="text-[var(--console-accent)]"
                disabled={busy}
                onClick={() => {
                  void onForgotPassword(signInEmail);
                }}
                type="button"
              >
                Forgot password?
              </button>
            ) : (
              <span />
            )}
            <p className="text-right text-xs uppercase tracking-[0.14em] text-[var(--console-muted)]">
              Need access? Contact a Sentinel admin for an invitation.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
