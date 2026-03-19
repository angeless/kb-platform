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

export default function ModelProvidersPage() {
  const [providers, setProviders] = useState<Provider[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");
  const [showAdd, setShowAdd] = useState(false);
  const [name, setName] = useState("openai");
  const [apiKey, setApiKey] = useState("");
  const [baseUrl, setBaseUrl] = useState("");
  const [adding, setAdding] = useState(false);

  const fetchProviders = async () => {
    try {
      const resp = await api.get<Provider[]>("/v1/model-providers");
      setProviders(resp.data);
    } catch (e) {
      setError(e instanceof ApiClientError ? e.message : "加载失败");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => { fetchProviders(); }, []);

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    setAdding(true);
    try {
      await api.post("/v1/model-providers", {
        provider_name: name,
        api_key: apiKey,
        base_url: baseUrl || null,
      });
      setShowAdd(false);
      setApiKey("");
      setBaseUrl("");
      await fetchProviders();
    } catch (e) {
      setError(e instanceof ApiClientError ? e.message : "添加失败");
    } finally {
      setAdding(false);
    }
  };

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">模型配置</h1>
        <button onClick={() => setShowAdd(!showAdd)} className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700">
          添加供应商
        </button>
      </div>

      {error && <div className="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-600">{error}</div>}

      {showAdd && (
        <form onSubmit={handleAdd} className="mb-6 rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">供应商</label>
              <select value={name} onChange={(e) => setName(e.target.value)} className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm">
                <option value="openai">OpenAI</option>
                <option value="anthropic">Anthropic</option>
                <option value="google">Google</option>
                <option value="deepseek">DeepSeek</option>
                <option value="custom">自定义</option>
              </select>
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">API Key</label>
              <input type="password" value={apiKey} onChange={(e) => setApiKey(e.target.value)} className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm" placeholder="sk-..." />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">Base URL（可选）</label>
              <input type="text" value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)} className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm" placeholder="https://api.openai.com" />
            </div>
          </div>
          <button type="submit" disabled={adding || !apiKey} className="mt-4 rounded-lg bg-primary-600 px-4 py-2 text-sm text-white disabled:opacity-50">
            {adding ? "添加中..." : "添加"}
          </button>
        </form>
      )}

      {isLoading ? (
        <div className="py-12 text-center text-gray-400">加载中...</div>
      ) : providers.length === 0 ? (
        <div className="py-12 text-center text-gray-400">暂无模型供应商，点击"添加供应商"开始配置</div>
      ) : (
        <div className="space-y-3">
          {providers.map((p) => (
            <div key={p.id} className="flex items-center justify-between rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
              <div>
                <div className="flex items-center gap-3">
                  <h3 className="font-semibold text-gray-900">{p.provider_name}</h3>
                  <StatusBadge status={p.status} />
                </div>
                <p className="mt-1 text-xs text-gray-400">Key: {p.api_key_masked}</p>
                {p.base_url && <p className="text-xs text-gray-400">{p.base_url}</p>}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
