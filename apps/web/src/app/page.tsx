"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/stores/auth-store";

export default function HomePage() {
  const router = useRouter();
  const { checkAuth, user } = useAuthStore();

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  useEffect(() => {
    if (user) {
      router.replace("/projects");
    } else {
      router.replace("/login");
    }
  }, [user, router]);

  return (
    <div className="flex min-h-screen items-center justify-center">
      <div className="text-gray-400">加载中...</div>
    </div>
  );
}
