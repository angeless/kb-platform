"use client";

import { useEffect, useState } from "react";
import { api, ApiClientError } from "@/lib/api";
import { StatusBadge } from "@/components/status-badge";

interface Provider {
  id: string;
  provider_name: string;
  base_url: string | null;
  api_key_masked: string;
  status: string;
  created_at: string;
}

interface Route {
  id: string;
  task_type: string;
  provider_id: string;
  model_name: string;
  priority: number;
}

export default function ModelSettingsPage() {
  const [providers, setProviders] = useState<Provider[]>([]);
  const [routes, setRoutes] = useState<Route[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  // Add provider form
  const [showAdd, setShowAdd] = useState(false);
  const [formName, setFormName] = useState("");
  const [formKey, setFormKey] = useState("");
  const [formUrl, setFormUrl] = useState("");
  const [saving, setSaving] = useState(false);

  const fetchData = async () => {
    setIsLoading(true);
    try {
      const [p, r] = await Promise.all([
        api.get<Provider[]>("/v1/model-providers"),
        api.get<Route[]>("/v1/model-routes"),
      ]);
      setProviders(p.data);
      setRoutes(r.data);
    } catch (e) {
      setError(e instanceof ApiClientError ? e.message : "加载失败");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => { fetchData(); }, []);

  const handleAddProvider = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError("");
    try {
      await api.post("/v1/model-providers", {
        provider_name: formName,
        api_key: formKey,
        base_url: formUrl || null,
      });
      setShowAdd(false);
      setFormName(""); setFormKey(""); setFormUrl("");
      await fetchData();
    } catch (e) {
      setError(e instanceof ApiClientError ? e.message : "添加失败");
    } finally {
      setSaving(false);
    }
  };

  const handleTest = async (providerId: string) => {
    try {
      const resp = await api.post<{ success: boolean }>("/v1/model-providers/test", {
        provider_id: providerId,
      });
      alert(resp.data.success ? "连通性测试成功" : "连通性测试失败");
    } catch (e) {
      alert(e instanceof ApiClientError ? e.message : "测试失败");
    }
  };

  if (isLoading) return <div className="py-12 text-center text-gray-400">加载中...</div>;

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">模型配置</h1>
        <button
          onClick={() => setShowAdd(!showAdd)}
          className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700"
        >
          添加供应商
        </button>
      </div>

      {error && <div className="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-600">{error}</div>}

      {/* Add Provider Form */}
      {showAdd && (
        <div className="mb-6 rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
          <h2 className="mb-4 font-semibold">添加模型供应商</h2>
          <form onSubmit={handleAddProvider} className="space-y-3">
            <div className="grid grid-cols-3 gap-3">
              <div>
                <label className="mb-1 block text-xs font-medium text-gray-600">供应商名称</label>
                <input value={formName} onChange={(e) => setFormName(e.target.value)}
                  placeholder="openai / anthropic / deepseek"
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none" />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-gray-600">API Key</label>
                <input type="password" value={formKey} onChange={(e) => setFormKey(e.target.value)}
                  placeholder="sk-..."
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none" />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-gray-600">Base URL (可选)</label>
                <input value={formUrl} onChange={(e) => setFormUrl(e.target.value)}
                  placeholder="https://api.openai.com/v1"
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none" />
              </div>
            </div>
            <div className="flex gap-2">
              <button type="submit" disabled={saving || !formName || !formKey}
                className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50">
                {saving ? "保存中..." : "保存"}
              </button>
              <button type="button" onClick={() => setShowAdd(false)}
                className="text-sm text-gray-500 hover:text-gray-700">取消</button>
            </div>
          </form>
        </div>
      )}

      {/* Providers List */}
      <div className="mb-8 rounded-xl border border-gray-200 bg-white shadow-sm">
        <div className="border-b border-gray-200 px-5 py-4">
          <h2 className="font-semibold text-gray-900">供应商 ({providers.length})</h2>
        </div>
        {providers.length === 0 ? (
          <div className="px-5 py-8 text-center text-gray-400">暂无供应商</div>
        ) : (
          <table className="w-full text-sm">
            <thead className="border-b border-gray-200 bg-gray-50">
              <tr>
                <th className="px-5 py-3 text-left font-medium text-gray-600">名称</th>
                <th className="px-5 py-3 text-left font-medium text-gray-600">API Key</th>
                <th className="px-5 py-3 text-left font-medium text-gray-600">Base URL</th>
                <th className="px-5 py-3 text-left font-medium text-gray-600">状态</th>
                <th className="px-5 py-3 text-left font-medium text-gray-600">操作</th>
              </tr>
            </thead>
            <tbody>
              {providers.map((p) => (
                <tr key={p.id} className="border-b border-gray-100 last:border-0">
                  <td className="px-5 py-3 font-medium">{p.provider_name}</td>
                  <td className="px-5 py-3 font-mono text-xs text-gray-400">{p.api_key_masked}</td>
                  <td className="px-5 py-3 text-gray-500">{p.base_url || "默认"}</td>
                  <td className="px-5 py-3"><StatusBadge status={p.status} /></td>
                  <td className="px-5 py-3">
                    <button onClick={() => handleTest(p.id)}
                      className="text-sm text-primary-600 hover:underline">测试连通</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Routes List */}
      <div className="rounded-xl border border-gray-200 bg-white shadow-sm">
        <div className="border-b border-gray-200 px-5 py-4">
          <h2 className="font-semibold text-gray-900">路由规则 ({routes.length})</h2>
        </div>
        {routes.length === 0 ? (
          <div className="px-5 py-8 text-center text-gray-400">暂无路由规则</div>
        ) : (
          <table className="w-full text-sm">
            <thead className="border-b border-gray-200 bg-gray-50">
              <tr>
                <th className="px-5 py-3 text-left font-medium text-gray-600">任务类型</th>
                <th className="px-5 py-3 text-left font-medium text-gray-600">模型</th>
                <th className="px-5 py-3 text-left font-medium text-gray-600">优先级</th>
              </tr>
            </thead>
            <tbody>
              {routes.map((r) => (
                <tr key={r.id} className="border-b border-gray-100 last:border-0">
                  <td className="px-5 py-3">{r.task_type}</td>
                  <td className="px-5 py-3 font-mono text-xs">{r.model_name}</td>
                  <td className="px-5 py-3">{r.priority}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
