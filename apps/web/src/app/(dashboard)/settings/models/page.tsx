"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, ApiClientError } from "@/lib/api";
import { usePermission } from "@/hooks/usePermission";
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
  cost_limit_usd: string | null;
}

const TASK_TYPE_LABELS: Record<string, string> = {
  embedding: "向量嵌入",
  classification: "内容分类",
  architecture: "架构生成",
  doc_generation: "文档生成",
  summary: "摘要生成",
  qa: "知识问答",
};

const TASK_TYPE_OPTIONS = Object.entries(TASK_TYPE_LABELS);

type Tab = "providers" | "routes";

export default function ModelSettingsPage() {
  const { hasRole } = usePermission();
  const router = useRouter();

  const [tab, setTab] = useState<Tab>("providers");
  const [providers, setProviders] = useState<Provider[]>([]);
  const [routes, setRoutes] = useState<Route[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");
  const [actionMsg, setActionMsg] = useState("");

  // Add provider form
  const [showAddProvider, setShowAddProvider] = useState(false);
  const [formName, setFormName] = useState("");
  const [formKey, setFormKey] = useState("");
  const [formUrl, setFormUrl] = useState("");
  const [saving, setSaving] = useState(false);

  // Add/edit route modal
  const [showRouteModal, setShowRouteModal] = useState(false);
  const [editRouteId, setEditRouteId] = useState<string | null>(null);
  const [routeTaskType, setRouteTaskType] = useState("embedding");
  const [routeProviderId, setRouteProviderId] = useState("");
  const [routeModelName, setRouteModelName] = useState("");
  const [routePriority, setRoutePriority] = useState(0);
  const [routeSaving, setRouteSaving] = useState(false);

  // Permission guard
  useEffect(() => {
    if (!hasRole("tenant_admin")) {
      router.replace("/projects");
    }
  }, [hasRole, router]);

  const fetchData = useCallback(async () => {
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
  }, []);

  useEffect(() => {
    if (hasRole("tenant_admin")) fetchData();
  }, [fetchData, hasRole]);

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
      setShowAddProvider(false);
      setFormName(""); setFormKey(""); setFormUrl("");
      await fetchData();
    } catch (e) {
      setError(e instanceof ApiClientError ? e.message : "添加失败");
    } finally {
      setSaving(false);
    }
  };

  const handleTest = async (providerId: string) => {
    setActionMsg("");
    try {
      const resp = await api.post<{ success: boolean }>("/v1/model-providers/test", {
        provider_id: providerId,
      });
      setActionMsg(resp.data.success ? "连通性测试成功" : "连通性测试失败");
    } catch (e) {
      setActionMsg(e instanceof ApiClientError ? e.message : "测试失败");
    }
  };

  const openAddRoute = () => {
    setEditRouteId(null);
    setRouteTaskType("embedding");
    setRouteProviderId(providers[0]?.id ?? "");
    setRouteModelName("");
    setRoutePriority(0);
    setShowRouteModal(true);
  };

  const openEditRoute = (route: Route) => {
    setEditRouteId(route.id);
    setRouteTaskType(route.task_type);
    setRouteProviderId(route.provider_id);
    setRouteModelName(route.model_name);
    setRoutePriority(route.priority);
    setShowRouteModal(true);
  };

  const handleSaveRoute = async () => {
    setRouteSaving(true);
    setActionMsg("");
    try {
      if (editRouteId) {
        await api.patch(`/v1/model-routes/${editRouteId}`, {
          model_name: routeModelName,
          priority: routePriority,
        });
      } else {
        await api.post("/v1/model-routes", {
          task_type: routeTaskType,
          provider_id: routeProviderId,
          model_name: routeModelName,
          priority: routePriority,
        });
      }
      setShowRouteModal(false);
      await fetchData();
    } catch (e) {
      setActionMsg(e instanceof ApiClientError ? e.message : "保存失败");
    } finally {
      setRouteSaving(false);
    }
  };

  const handleDeleteRoute = async (routeId: string) => {
    setActionMsg("");
    try {
      await api.del(`/v1/model-routes/${routeId}`);
      await fetchData();
    } catch (e) {
      setActionMsg(e instanceof ApiClientError ? e.message : "删除失败");
    }
  };

  if (!hasRole("tenant_admin")) return null;
  if (isLoading) return <div className="py-12 text-center text-gray-400">加载中...</div>;

  return (
    <div className="mx-auto max-w-5xl">
      <h1 className="mb-6 text-2xl font-bold text-gray-900">全局设置</h1>

      {/* Tabs */}
      <div className="mb-6 flex border-b border-gray-200">
        <button
          onClick={() => setTab("providers")}
          className={`border-b-2 px-4 py-2 text-sm ${tab === "providers" ? "border-primary-600 font-medium text-primary-600" : "border-transparent text-gray-500 hover:text-gray-700"}`}
        >
          模型提供商
        </button>
        <button
          onClick={() => setTab("routes")}
          className={`border-b-2 px-4 py-2 text-sm ${tab === "routes" ? "border-primary-600 font-medium text-primary-600" : "border-transparent text-gray-500 hover:text-gray-700"}`}
        >
          路由规则
        </button>
      </div>

      {error && <div className="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-600">{error}</div>}
      {actionMsg && (
        <div className={`mb-4 rounded-lg p-3 text-sm ${actionMsg.includes("成功") ? "bg-green-50 text-green-600" : "bg-red-50 text-red-600"}`}>
          {actionMsg}
        </div>
      )}

      {/* Tab 1: Providers */}
      {tab === "providers" && (
        <>
          <div className="mb-4 flex justify-end">
            <button onClick={() => setShowAddProvider(!showAddProvider)}
              className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700">
              添加供应商
            </button>
          </div>

          {showAddProvider && (
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
                  <button type="button" onClick={() => setShowAddProvider(false)}
                    className="text-sm text-gray-500 hover:text-gray-700">取消</button>
                </div>
              </form>
            </div>
          )}

          <div className="rounded-xl border border-gray-200 bg-white shadow-sm">
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
        </>
      )}

      {/* Tab 2: Routes */}
      {tab === "routes" && (
        <>
          <div className="mb-4 flex justify-end">
            <button onClick={openAddRoute}
              className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700">
              添加路由
            </button>
          </div>

          <div className="rounded-xl border border-gray-200 bg-white shadow-sm">
            {routes.length === 0 ? (
              <div className="px-5 py-8 text-center text-gray-400">暂无路由规则</div>
            ) : (
              <table className="w-full text-sm">
                <thead className="border-b border-gray-200 bg-gray-50">
                  <tr>
                    <th className="px-5 py-3 text-left font-medium text-gray-600">任务类型</th>
                    <th className="px-5 py-3 text-left font-medium text-gray-600">供应商</th>
                    <th className="px-5 py-3 text-left font-medium text-gray-600">模型</th>
                    <th className="px-5 py-3 text-left font-medium text-gray-600">优先级</th>
                    <th className="px-5 py-3 text-left font-medium text-gray-600">操作</th>
                  </tr>
                </thead>
                <tbody>
                  {routes.map((r) => {
                    const providerName = providers.find((p) => p.id === r.provider_id)?.provider_name ?? r.provider_id.slice(0, 8);
                    return (
                      <tr key={r.id} className="border-b border-gray-100 last:border-0">
                        <td className="px-5 py-3">
                          <span className="rounded bg-gray-100 px-2 py-0.5 text-xs">
                            {TASK_TYPE_LABELS[r.task_type] ?? r.task_type}
                          </span>
                        </td>
                        <td className="px-5 py-3 text-gray-600">{providerName}</td>
                        <td className="px-5 py-3 font-mono text-xs">{r.model_name}</td>
                        <td className="px-5 py-3">{r.priority}</td>
                        <td className="px-5 py-3 flex gap-3">
                          <button onClick={() => openEditRoute(r)}
                            className="text-sm text-primary-600 hover:underline">修改</button>
                          <button onClick={() => handleDeleteRoute(r.id)}
                            className="text-sm text-red-500 hover:underline">删除</button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </div>
        </>
      )}

      {/* Route Modal */}
      {showRouteModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-lg">
            <h3 className="text-lg font-semibold text-gray-900">
              {editRouteId ? "修改路由规则" : "添加路由规则"}
            </h3>

            <div className="mt-4 space-y-4">
              <div>
                <label className="text-sm text-gray-600">任务类型</label>
                <select value={routeTaskType} onChange={(e) => setRouteTaskType(e.target.value)}
                  disabled={!!editRouteId}
                  className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none disabled:bg-gray-100">
                  {TASK_TYPE_OPTIONS.map(([value, label]) => (
                    <option key={value} value={value}>{label} ({value})</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-sm text-gray-600">供应商</label>
                <select value={routeProviderId} onChange={(e) => setRouteProviderId(e.target.value)}
                  disabled={!!editRouteId}
                  className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none disabled:bg-gray-100">
                  {providers.map((p) => (
                    <option key={p.id} value={p.id}>{p.provider_name}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-sm text-gray-600">模型名称</label>
                <input type="text" value={routeModelName} onChange={(e) => setRouteModelName(e.target.value)}
                  placeholder="gpt-4o / claude-3-sonnet..."
                  className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none" />
              </div>
              <div>
                <label className="text-sm text-gray-600">优先级（数字越大优先级越高）</label>
                <input type="number" value={routePriority} onChange={(e) => setRoutePriority(Number(e.target.value))}
                  className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none" />
              </div>
            </div>

            <div className="mt-6 flex justify-end gap-3">
              <button onClick={() => setShowRouteModal(false)}
                className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50">
                取消
              </button>
              <button onClick={handleSaveRoute} disabled={routeSaving || !routeModelName}
                className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50">
                {routeSaving ? "保存中..." : "保存"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
