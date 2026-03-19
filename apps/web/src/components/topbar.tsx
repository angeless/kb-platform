"use client";

import { useRouter } from "next/navigation";
import { useAuthStore } from "@/stores/auth-store";

export function Topbar() {
  const router = useRouter();
  const { user, logout } = useAuthStore();

  const handleLogout = () => {
    logout();
    router.push("/login");
  };

  return (
    <header className="flex h-14 items-center justify-between border-b border-gray-200 bg-white px-6">
      <div />
      <div className="flex items-center gap-4">
        <span className="text-sm text-gray-500">{user?.email}</span>
        <span className="rounded bg-primary-50 px-2 py-0.5 text-xs font-medium text-primary-700">
          {user?.role}
        </span>
        <button
          onClick={handleLogout}
          className="text-sm text-gray-500 hover:text-gray-700"
        >
          退出
        </button>
      </div>
    </header>
  );
}
