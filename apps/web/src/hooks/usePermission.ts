/**
 * RBAC permission hook — checks if the current user has permission for an action.
 *
 * Role hierarchy (matches backend deps.py ROLE_HIERARCHY):
 *   viewer(0) < editor(1) < reviewer(2) < project_admin(3) < tenant_admin(4) < platform_admin(5)
 */

import { useAuthStore } from "@/stores/auth-store";

const ROLE_LEVEL: Record<string, number> = {
  viewer: 0,
  editor: 1,
  reviewer: 2,
  project_admin: 3,
  tenant_admin: 4,
  admin: 4, // legacy alias
  platform_admin: 5,
};

const ACTION_MIN_ROLE: Record<string, string> = {
  view: "viewer",
  edit: "editor",
  review: "reviewer",
  publish: "reviewer",
  manage_project: "project_admin",
  delete_project: "project_admin",
  manage_users: "tenant_admin",
  manage_models: "tenant_admin",
};

export function usePermission() {
  const user = useAuthStore((s) => s.user);
  const userLevel = ROLE_LEVEL[user?.role ?? ""] ?? -1;

  function can(action: string): boolean {
    const minRole = ACTION_MIN_ROLE[action];
    if (!minRole) return false;
    return userLevel >= (ROLE_LEVEL[minRole] ?? 99);
  }

  function hasRole(minimumRole: string): boolean {
    return userLevel >= (ROLE_LEVEL[minimumRole] ?? 99);
  }

  return { can, hasRole, role: user?.role ?? null };
}
