"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

/**
 * Session expiry guard — wraps dashboard layout.
 * Listens for a custom event dispatched when refresh token fails.
 * Shows a modal instead of immediately redirecting, giving the user time to react.
 */
export function SessionGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [expired, setExpired] = useState(false);

  useEffect(() => {
    const handler = () => setExpired(true);
    window.addEventListener("session-expired", handler);
    return () => window.removeEventListener("session-expired", handler);
  }, []);

  const handleLogin = () => {
    setExpired(false);
    router.push("/login");
  };

  return (
    <>
      {children}
      {expired && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="w-full max-w-sm rounded-xl bg-white p-6 shadow-xl text-center">
            <div className="mb-4 text-4xl">🔒</div>
            <h3 className="mb-2 text-lg font-semibold text-gray-900">登录已过期</h3>
            <p className="mb-6 text-sm text-gray-500">
              您的登录会话已过期，请重新登录以继续使用。
            </p>
            <button
              onClick={handleLogin}
              className="rounded-lg bg-primary-600 px-6 py-2.5 text-sm font-medium text-white hover:bg-primary-700"
            >
              重新登录
            </button>
          </div>
        </div>
      )}
    </>
  );
}
