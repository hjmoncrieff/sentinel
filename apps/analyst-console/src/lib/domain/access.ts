import type {
  AppRole,
  InviteRole,
  NotificationRecipientRole,
} from "@/lib/domain/types";

export function normalizeRole(role?: string | null): AppRole {
  if (role === "admin" || role === "ra" || role === "coordinator") {
    return role;
  }

  return "analyst";
}

export function canPublish(role?: string | null): boolean {
  if (!role) {
    return false;
  }

  return normalizeRole(role) !== "ra";
}

export function canSeeRestrictedIntel(role?: string | null): boolean {
  if (!role) {
    return false;
  }

  const normalized = normalizeRole(role);
  return normalized === "analyst" || normalized === "coordinator" || normalized === "admin";
}

export function canAdministerAccess(role?: string | null): boolean {
  if (!role) {
    return false;
  }

  return normalizeRole(role) === "admin";
}

export function labelRole(role?: string | null): string {
  const normalized = normalizeRole(role);

  if (normalized === "ra") {
    return "RA";
  }

  if (normalized === "admin") {
    return "Admin";
  }

  if (normalized === "coordinator") {
    return "Analyst";
  }

  return "Analyst";
}

export function labelNotificationAudience(
  role: NotificationRecipientRole,
): string {
  if (role === "ra") {
    return "RAs";
  }

  if (role === "admin") {
    return "Admins";
  }

  return "Analysts";
}

export function labelInviteRole(role: InviteRole): string {
  if (role === "ra") {
    return "RA";
  }

  if (role === "admin") {
    return "Admin";
  }

  return "Analyst";
}
