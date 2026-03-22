"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/stores/auth-store";
import { Sidebar } from "@/components/sidebar";
import { Topbar } from "@/components/topbar";
import { SessionGuard } from "@/components/session-guard";
import { ToastContainer } from "@/components/error-toast";
import { SkeletonList } from "@/components/skeleton-card";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const { user, checkAuth } = useAuthStore();

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  useEffect(() => {
    if (user === null && typeof window !== "undefined") {
      const token = localStorage.getItem("access_token");
      if (!token) {
        router.replace("/login");
      }
    }
  }, [user, router]);

  if (!user) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50">
        <div className="w-full max-w-2xl px-6">
          <SkeletonList count={3} />
        </div>
      </div>
    );
  }

  return (
    <SessionGuard>
      <div className="flex h-screen overflow-hidden">
        <Sidebar />
        <div className="flex flex-1 flex-col overflow-hidden">
          <Topbar />
          <main className="flex-1 overflow-y-auto bg-gray-50 p-6">
            {children}
          </main>
        </div>
      </div>
      <ToastContainer />
    </SessionGuard>
  );
}
