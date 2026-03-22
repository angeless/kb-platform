"use client";

import { useState } from "react";
import Link from "next/link";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [resetToken, setResetToken] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    if (!email.trim()) {
      setError("请输入邮箱");
      return;
    }

    setIsLoading(true);
    try {
      const resp = await fetch(`${API_BASE}/v1/auth/forgot-password`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });
      const json = await resp.json();
      setSubmitted(true);
      // Dev mode: show the token for testing
      if (json.data?.reset_token) {
        setResetToken(json.data.reset_token);
      }
    } catch {
      setError("网络错误，请稍后重试");
    } finally {
      setIsLoading(false);
    }
  };

  if (submitted) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4">
        <div className="w-full max-w-md">
          <div className="rounded-xl border border-gray-200 bg-white p-8 shadow-sm">
            <h2 className="mb-4 text-xl font-semibold text-gray-900">已提交申请</h2>
            <p className="mb-6 text-sm text-gray-600">
              密码重置功能暂未开放自助服务，请联系团队管理员帮您重置密码。
            </p>

            {resetToken && (
              <div className="mb-6 rounded-lg bg-yellow-50 p-3 text-sm">
                <p className="font-medium text-yellow-800">开发模式 — 重置 Token:</p>
                <p className="mt-1 break-all font-mono text-xs text-yellow-700">
                  {resetToken}
                </p>
                <Link
                  href={`/reset-password?token=${resetToken}`}
                  className="mt-2 inline-block text-sm text-primary-600 hover:underline"
                >
                  点击此处重置密码 →
                </Link>
              </div>
            )}

            <Link
              href="/login"
              className="block text-center text-sm text-primary-600 hover:underline"
            >
              返回登录
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4">
      <div className="w-full max-w-md">
        <div className="mb-8 text-center">
          <h1 className="text-3xl font-bold text-gray-900">KB Platform</h1>
          <p className="mt-2 text-gray-500">重置您的密码</p>
        </div>

        <div className="rounded-xl border border-gray-200 bg-white p-8 shadow-sm">
          <h2 className="mb-2 text-xl font-semibold">忘记密码</h2>
          <p className="mb-6 text-sm text-gray-500">
            输入您的邮箱地址，提交后将由管理员协助重置密码。
          </p>

          {error && (
            <div className="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-600">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                邮箱
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                placeholder="your@email.com"
              />
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full rounded-lg bg-primary-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
            >
              {isLoading ? "提交中..." : "提交重置申请"}
            </button>
          </form>

          <p className="mt-4 text-center text-sm text-gray-500">
            <Link href="/login" className="text-primary-600 hover:underline">
              返回登录
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
