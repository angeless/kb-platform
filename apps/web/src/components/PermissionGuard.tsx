"use client";

import { type ReactNode } from "react";
import { usePermission } from "@/hooks/usePermission";

interface PermissionGuardProps {
  /** Named action from ACTION_MIN_ROLE (e.g. "edit", "review", "manage_project") */
  action?: string;
  /** Or specify a minimum role directly (e.g. "editor", "tenant_admin") */
  minimumRole?: string;
  children: ReactNode;
}

/**
 * Renders children only if the current user has sufficient permission.
 * Does NOT render a disabled/hidden version — the DOM element is simply absent.
 */
export function PermissionGuard({ action, minimumRole, children }: PermissionGuardProps) {
  const { can, hasRole } = usePermission();

  if (action && !can(action)) return null;
  if (minimumRole && !hasRole(minimumRole)) return null;

  return <>{children}</>;
}
