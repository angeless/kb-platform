"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { usePermission } from "@/hooks/usePermission";

interface NavItem {
  label: string;
  href: string;
  icon: string;
  minRole?: string;
}

const navItems: NavItem[] = [
  { label: "项目", href: "/projects", icon: "📁" },
  { label: "全局设置", href: "/settings/models", icon: "⚙️", minRole: "tenant_admin" },
  { label: "操作日志", href: "/admin/audit-logs", icon: "📋", minRole: "tenant_admin" },
];

export function Sidebar() {
  const pathname = usePathname();
  const { hasRole } = usePermission();

  return (
    <aside className="flex h-screen w-56 flex-col border-r border-gray-200 bg-white">
      <div className="flex h-14 items-center border-b border-gray-200 px-4">
        <Link href="/projects" className="text-lg font-bold text-primary-600">
          KB Platform
        </Link>
      </div>

      <nav className="flex-1 overflow-y-auto p-3">
        <ul className="space-y-1">
          {navItems
            .filter((item) => !item.minRole || hasRole(item.minRole))
            .map((item) => {
            const isActive = pathname.startsWith(item.href);
            return (
              <li key={item.href}>
                <Link
                  href={item.href}
                  className={cn(
                    "flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm transition-colors",
                    isActive
                      ? "bg-primary-50 font-medium text-primary-700"
                      : "text-gray-600 hover:bg-gray-100 hover:text-gray-900",
                  )}
                >
                  <span className="text-base">{item.icon}</span>
                  {item.label}
                </Link>
              </li>
            );
          })}
        </ul>

      </nav>
    </aside>
  );
}
