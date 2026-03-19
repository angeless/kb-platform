"use client";

import { useEffect, useState } from "react";
import { api, ApiClientError } from "@/lib/api";

interface UserItem {
  id: string;
  email: string;
  role: string;
  status: string;
  created_at: string;
}

const roleLabels: Record<string, string> = {
  platform_admin: "平台管理员",
  tenant_admin: "租户管理员",
  project_admin: "项目管理员",
  editor: "编辑",
  reviewer: "审核员",
  viewer: "查看者",
};

export default function UsersPage() {
  const [users, setUsers] = useState<UserItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");
  const [showInvite, setShowInvite] = useState(false);
  const [email, setEmail] = useState("");
  const [role, setRole] = useState("editor");
  const [inviting, setInviting] = useState(false);

  const fetchUsers = async () => {
    try {
      const resp = await api.get<UserItem[]>("/v1/users");
      setUsers(resp.data);
    } catch (e) {
      setError(e instanceof ApiClientError ? e.message : "加载失败");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => { fetchUsers(); }, []);

  const handleInvite = async (e: React.FormEvent) => {
    e.preventDefault();
    setInviting(true);
    try {
      await api.post("/v1/users/invite", { email, role });
      setShowInvite(false);
      setEmail("");
      await fetchUsers();
    } catch (e) {
      setError(e instanceof ApiClientError ? e.message : "邀请失败");
    } finally {
      setInviting(false);
    }
  };

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">用户管理</h1>
        <button onClick={() => setShowInvite(!showInvite)} className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700">
          邀请用户
        </button>
      </div>

      {error && <div className="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-600">{error}</div>}

      {showInvite && (
        <form onSubmit={handleInvite} className="mb-6 flex items-end gap-4 rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
          <div className="flex-1">
            <label className="mb-1 block text-sm font-medium text-gray-700">邮箱</label>
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm" placeholder="user@example.com" />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">角色</label>
            <select value={role} onChange={(e) => setRole(e.target.value)} className="rounded-lg border border-gray-300 px-3 py-2 text-sm">
              {Object.entries(roleLabels).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
          </div>
          <button type="submit" disabled={inviting || !email} className="rounded-lg bg-primary-600 px-4 py-2 text-sm text-white disabled:opacity-50">
            {inviting ? "邀请中..." : "发送邀请"}
          </button>
        </form>
      )}

      {isLoading ? (
        <div className="py-12 text-center text-gray-400">加载中...</div>
      ) : (
        <div className="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
          <table className="w-full text-sm">
            <thead className="border-b border-gray-200 bg-gray-50">
              <tr>
                <th className="px-5 py-3 text-left font-medium text-gray-600">邮箱</th>
                <th className="px-5 py-3 text-left font-medium text-gray-600">角色</th>
                <th className="px-5 py-3 text-left font-medium text-gray-600">状态</th>
                <th className="px-5 py-3 text-left font-medium text-gray-600">加入时间</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id} className="border-b border-gray-100 last:border-0">
                  <td className="px-5 py-3 font-medium text-gray-900">{u.email}</td>
                  <td className="px-5 py-3 text-gray-500">{roleLabels[u.role] || u.role}</td>
                  <td className="px-5 py-3">
                    <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${u.status === "active" ? "bg-green-50 text-green-700" : "bg-gray-100 text-gray-500"}`}>
                      {u.status === "active" ? "活跃" : "已禁用"}
                    </span>
                  </td>
                  <td className="px-5 py-3 text-gray-400">{new Date(u.created_at).toLocaleDateString("zh-CN")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
