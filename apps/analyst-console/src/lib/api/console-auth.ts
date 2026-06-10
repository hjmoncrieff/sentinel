import type { AuthChangeEvent, Session } from "@supabase/supabase-js";

import type { SessionProfile } from "@/lib/domain/types";
import { normalizeRole } from "@/lib/domain/access";
import { supabase } from "@/lib/supabase/client";

async function readProfileForSession(
  session: Session | null,
): Promise<SessionProfile | null> {
  if (!session?.user) {
    return null;
  }

  const { data, error, status } = await supabase
    .from("profiles")
    .select("id,email,display_name,role,active")
    .eq("id", session.user.id)
    .maybeSingle();

  if (error && status !== 406) {
    throw error;
  }

  return {
    id: session.user.id,
    email: data?.email ?? session.user.email ?? null,
    display_name:
      data?.display_name ??
      session.user.user_metadata?.display_name ??
      session.user.email?.split("@")[0] ??
      "Analyst",
    role: normalizeRole(data?.role),
    active: data?.active ?? true,
  };
}

export async function getSessionProfile(): Promise<SessionProfile | null> {
  const { data, error } = await supabase.auth.getSession();

  if (error) {
    throw error;
  }

  return readProfileForSession(data.session);
}

export function subscribeToAuthChanges(
  onChange: (profile: SessionProfile | null, event: AuthChangeEvent) => void,
): () => void {
  const { data } = supabase.auth.onAuthStateChange((event, session) => {
    void readProfileForSession(session)
      .then((profile) => onChange(profile, event))
      .catch(() => onChange(null, event));
  });

  return () => {
    data.subscription.unsubscribe();
  };
}

export async function signInConsoleUser(email: string, password: string) {
  const { error } = await supabase.auth.signInWithPassword({ email, password });

  if (error) {
    throw error;
  }
}

export async function registerConsoleUser(payload: {
  displayName: string;
  email: string;
  password: string;
}) {
  void payload;
  throw new Error(
    "Self-service registration is disabled. Access is provisioned by an admin invitation.",
  );
}

export async function requestConsolePasswordReset(
  email: string,
  redirectTo: string,
) {
  const { error } = await supabase.auth.resetPasswordForEmail(email, {
    redirectTo,
  });

  if (error) {
    throw error;
  }
}

export async function updateConsolePassword(password: string) {
  const { error } = await supabase.auth.updateUser({ password });

  if (error) {
    throw error;
  }
}

export function hasConsoleRecoveryToken(url?: string): boolean {
  if (typeof window === "undefined" && !url) {
    return false;
  }

  const target = url ?? window.location.href;
  return /(?:[#?]|&)type=recovery(?:&|$)/i.test(target);
}

export async function signOutConsoleUser() {
  const { error } = await supabase.auth.signOut();

  if (error) {
    throw error;
  }
}
