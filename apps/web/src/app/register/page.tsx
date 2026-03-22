"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuthStore } from "@/stores/auth-store";

export default function RegisterPage() {
  const router = useRouter();
  const { register, isLoading, error } = useAuthStore();
  const [tenantName, setTenantName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [localError, setLocalError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLocalError("");

    if (!tenantName.trim()) {
      setLocalError("请输入组织名称");
      return;
    }
    if (!email.trim()) {
      setLocalError("请输入邮箱");
      return;
    }
    if (password.length < 8) {
      setLocalError("密码至少 8 位");
      return;
    }
    if (!/[A-Z]/.test(password) || !/[0-9]/.test(password)) {
      setLocalError("密码需包含大写字母和数字");
      return;
    }
    if (password !== confirmPassword) {
      setLocalError("两次密码不一致");
      return;
    }

    try {
      await register(tenantName, email, password);
      router.push("/login?registered=true");
    } catch {
      // error is set in store
    }
  };

  const displayError = localError || error;

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4">
      <div className="w-full max-w-md">
        <div className="mb-8 text-center">
          <h1 className="text-3xl font-bold text-gray-900">KB Platform</h1>
          <p className="mt-2 text-gray-500">创建你的知识系统</p>
        </div>

        <div className="rounded-xl border border-gray-200 bg-white p-8 shadow-sm">
          <h2 className="mb-6 text-xl font-semibold">注册</h2>

          {displayError && (
            <div className="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-600">
              {displayError}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                团队名称
              </label>
              <input
                type="text"
                value={tenantName}
                onChange={(e) => setTenantName(e.target.value)}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                placeholder="你的公司或团队名称"
              />
            </div>

            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                邮箱
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                placeholder="admin@company.com"
              />
            </div>

            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                密码
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                placeholder="至少 8 位，含大写字母和数字"
              />
            </div>

            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                确认密码
              </label>
              <input
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                placeholder="再次输入密码"
              />
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full rounded-lg bg-primary-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
            >
              {isLoading ? "注册中..." : "注册"}
            </button>
          </form>

          <p className="mt-4 text-center text-sm text-gray-500">
            已有账号？{" "}
            <Link href="/login" className="text-primary-600 hover:underline">
              登录
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
