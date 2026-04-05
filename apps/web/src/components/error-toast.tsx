"use client";

import { useEffect, useState } from "react";

interface Toast {
  id: string;
  message: string;
  type: "error" | "warning" | "info";
}

let addToastFn: ((message: string, type?: Toast["type"]) => void) | null = null;

/**
 * Show an error toast from anywhere in the app.
 * Call without needing React context — works from api.ts interceptors.
 */
export function showErrorToast(message: string, type: Toast["type"] = "error") {
  if (addToastFn) {
    addToastFn(message, type);
  }
}

/**
 * Toast container — mount once in the root layout.
 * Displays auto-dismissing error/warning/info toasts.
 */
export function ToastContainer() {
  const [toasts, setToasts] = useState<Toast[]>([]);

  useEffect(() => {
    const timers = new Map<string, ReturnType<typeof setTimeout>>();

    addToastFn = (message: string, type: Toast["type"] = "error") => {
      const id = Date.now().toString(36) + Math.random().toString(36).slice(2);
      setToasts((prev) => [...prev.slice(-4), { id, message, type }]); // max 5 toasts

      // Auto-dismiss after 5 seconds
      const timer = setTimeout(() => {
        setToasts((prev) => prev.filter((t) => t.id !== id));
        timers.delete(id);
      }, 5000);
      timers.set(id, timer);
    };

    return () => {
      addToastFn = null;
      timers.forEach(clearTimeout);
      timers.clear();
    };
  }, []);

  if (toasts.length === 0) return null;

  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2">
      {toasts.map((toast) => (
        <div
          key={toast.id}
          className={`flex items-center gap-2 rounded-lg px-4 py-3 text-sm shadow-lg transition-all ${
            toast.type === "error"
              ? "bg-red-50 text-red-700 border border-red-200"
              : toast.type === "warning"
                ? "bg-yellow-50 text-yellow-700 border border-yellow-200"
                : "bg-blue-50 text-blue-700 border border-blue-200"
          }`}
        >
          <span>{toast.message}</span>
          <button
            onClick={() => setToasts((prev) => prev.filter((t) => t.id !== toast.id))}
            className="ml-2 opacity-50 hover:opacity-100"
          >
            ✕
          </button>
        </div>
      ))}
    </div>
  );
}
