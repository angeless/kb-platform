"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { PermissionGuard } from "@/components/PermissionGuard";

const navItems = [
  { label: "项目", href: "/projects", icon: "📁" },
];

const settingsItems = [
  { label: "模型配置", href: "/settings/models", icon: "🤖" },
  { label: "用户管理", href: "/settings/users", icon: "👥" },
  { label: "审计日志", href: "/settings/audit", icon: "📋" },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="flex h-screen w-56 flex-col border-r border-gray-200 bg-white">
      <div className="flex h-14 items-center border-b border-gray-200 px-4">
        <Link href="/projects" className="text-lg font-bold text-primary-600">
          KB Platform
        </Link>
      </div>

      <nav className="flex-1 overflow-y-auto p-3">
        <ul className="space-y-1">
          {navItems.map((item) => {
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

        <PermissionGuard action="manage_users">
          <div className="mt-6 border-t border-gray-200 pt-4">
            <p className="mb-2 px-3 text-xs font-medium uppercase text-gray-400">系统管理</p>
            <ul className="space-y-1">
              {settingsItems.map((item) => {
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
          </div>
        </PermissionGuard>
      </nav>
    </aside>
  );
}
