"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { api, ApiClientError } from "@/lib/api";

interface Project {
  id: string;
  name: string;
  industry_hint: string | null;
  status: string;
}

interface ApiKeyItem {
  id: string;
  name: string;
  key_prefix: string;
  is_active: boolean;
  created_at: string;
  last_used_at: string | null;
}

export default function ProjectSettingsPage() {
  const params = useParams();
  const router = useRouter();
  const projectId = params.id as string;

  const [project, setProject] = useState<Project | null>(null);
  const [name, setName] = useState("");
  const [industry, setIndustry] = useState("");
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  // API Key state
  const [apiKeys, setApiKeys] = useState<ApiKeyItem[]>([]);
  const [newKeyName, setNewKeyName] = useState("");
  const [creatingKey, setCreatingKey] = useState(false);
  const [showKeyModal, setShowKeyModal] = useState(false);
  const [rawKey, setRawKey] = useState("");
  const [revokeId, setRevokeId] = useState<string | null>(null);

  const fetchApiKeys = useCallback(async () => {
    try {
      const resp = await api.get<ApiKeyItem[]>(`/v1/projects/${projectId}/api-keys`);
      setApiKeys(resp.data);
    } catch (e) { console.error("Failed to load API keys", e); }
  }, [projectId]);

  useEffect(() => {
    const fetchProject = async () => {
      try {
        const resp = await api.get<Project>(`/v1/projects/${projectId}`);
        setProject(resp.data);
        setName(resp.data.name);
        setIndustry(resp.data.industry_hint || "");
      } catch (e) {
        setError(e instanceof ApiClientError ? e.message : "加载失败");
      }
    };
    fetchProject();
    fetchApiKeys();
  }, [projectId, fetchApiKeys]);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setMessage("");
    setError("");
    try {
      await api.patch(`/v1/projects/${projectId}`, {
        name,
        industry_hint: industry || null,
      });
      setMessage("保存成功");
    } catch (e) {
      setError(e instanceof ApiClientError ? e.message : "保存失败");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    setDeleting(true);
    try {
      await api.del(`/v1/projects/${projectId}`);
      router.push("/projects");
    } catch (e) {
      setError(e instanceof ApiClientError ? e.message : "删除失败");
      setDeleting(false);
    }
  };

  const handleCreateKey = async () => {
    if (!newKeyName.trim()) return;
    setCreatingKey(true);
    try {
      const resp = await api.post<{ raw_key: string }>(`/v1/projects/${projectId}/api-keys`, {
        name: newKeyName.trim(),
      });
      setRawKey(resp.data.raw_key);
      setShowKeyModal(true);
      setNewKeyName("");
      fetchApiKeys();
    } catch (e) {
      setError(e instanceof ApiClientError ? e.message : "创建 API Key 失败");
    } finally {
      setCreatingKey(false);
    }
  };

  const handleRevokeKey = async (keyId: string) => {
    try {
      await api.del(`/v1/projects/${projectId}/api-keys/${keyId}`);
      setRevokeId(null);
      fetchApiKeys();
    } catch (e) {
      setError(e instanceof ApiClientError ? e.message : "撤销失败");
    }
  };

  if (!project && !error) {
    return <div className="py-12 text-center text-gray-400">加载中...</div>;
  }

  return (
    <div className="mx-auto max-w-2xl">
      <div className="mb-6">
        <Link href={`/projects/${projectId}`} className="text-sm text-primary-600 hover:underline">
          ← 返回项目
        </Link>
        <h1 className="mt-2 text-2xl font-bold text-gray-900">项目设置</h1>
      </div>

      {message && (
        <div className="mb-4 rounded-lg bg-green-50 p-3 text-sm text-green-600">{message}</div>
      )}
      {error && (
        <div className="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-600">{error}</div>
      )}

      {/* Basic Settings */}
      <div className="mb-6 rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
        <h2 className="mb-4 text-lg font-semibold">基本信息</h2>
        <form onSubmit={handleSave} className="space-y-4">
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">项目名称</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">行业</label>
            <input
              type="text"
              value={industry}
              onChange={(e) => setIndustry(e.target.value)}
              placeholder="可选"
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
            />
          </div>
          <button
            type="submit"
            disabled={saving}
            className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
          >
            {saving ? "保存中..." : "保存"}
          </button>
        </form>
      </div>

      {/* API Key Management */}
      <div className="mb-6 rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
        <h2 className="mb-4 text-lg font-semibold">API 访问</h2>
        <p className="mb-4 text-sm text-gray-500">
          创建 API Key 供外部 Agent 调用知识检索和问答接口。Key 仅在创建时展示一次。
        </p>

        {/* Create Key */}
        <div className="mb-4 flex gap-2">
          <input
            type="text"
            value={newKeyName}
            onChange={(e) => setNewKeyName(e.target.value)}
            placeholder="Key 名称（如：生产环境）"
            className="flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
          />
          <button
            onClick={handleCreateKey}
            disabled={creatingKey || !newKeyName.trim()}
            className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
          >
            {creatingKey ? "创建中..." : "创建 Key"}
          </button>
        </div>

        {/* Key List */}
        {apiKeys.length > 0 ? (
          <div className="divide-y divide-gray-100 rounded-lg border border-gray-200">
            {apiKeys.map((k) => (
              <div key={k.id} className="flex items-center justify-between px-4 py-3">
                <div>
                  <span className="text-sm font-medium text-gray-900">{k.name}</span>
                  <span className="ml-2 font-mono text-xs text-gray-400">{k.key_prefix}...</span>
                  {!k.is_active && (
                    <span className="ml-2 rounded bg-red-100 px-1.5 py-0.5 text-xs text-red-600">已撤销</span>
                  )}
                </div>
                <div className="flex items-center gap-3 text-xs text-gray-400">
                  {k.last_used_at && <span>最近使用: {new Date(k.last_used_at).toLocaleDateString()}</span>}
                  <span>{new Date(k.created_at).toLocaleDateString()}</span>
                  {k.is_active && (
                    revokeId === k.id ? (
                      <span className="flex items-center gap-1">
                        <button onClick={() => handleRevokeKey(k.id)} className="text-red-600 hover:underline">确认撤销</button>
                        <button onClick={() => setRevokeId(null)} className="text-gray-500 hover:underline">取消</button>
                      </span>
                    ) : (
                      <button onClick={() => setRevokeId(k.id)} className="text-red-500 hover:underline">撤销</button>
                    )
                  )}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-gray-400">暂无 API Key</p>
        )}
      </div>

      {/* Raw Key Modal */}
      {showKeyModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl">
            <h3 className="mb-2 text-lg font-semibold text-gray-900">API Key 已创建</h3>
            <p className="mb-3 text-sm text-amber-600">请立即复制，关闭后不可再查看。</p>
            <div className="mb-4 rounded-lg bg-gray-100 p-3 font-mono text-sm text-gray-800 break-all select-all">
              {rawKey}
            </div>
            <div className="flex justify-end gap-2">
              <button
                onClick={() => { navigator.clipboard.writeText(rawKey); }}
                className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700"
              >
                复制
              </button>
              <button
                onClick={() => { setShowKeyModal(false); setRawKey(""); }}
                className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-600 hover:bg-gray-50"
              >
                关闭
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Danger Zone */}
      <div className="rounded-xl border border-red-200 bg-white p-6 shadow-sm">
        <h2 className="mb-2 text-lg font-semibold text-red-600">危险区域</h2>
        <p className="mb-4 text-sm text-gray-500">删除项目后，所有资料、文档、架构将不可恢复。</p>
        {!confirmDelete ? (
          <button
            onClick={() => setConfirmDelete(true)}
            className="rounded-lg border border-red-300 px-4 py-2 text-sm font-medium text-red-600 hover:bg-red-50"
          >
            删除项目
          </button>
        ) : (
          <div className="flex items-center gap-3">
            <span className="text-sm text-red-600">确认删除？此操作不可撤销。</span>
            <button
              onClick={handleDelete}
              disabled={deleting}
              className="rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-50"
            >
              {deleting ? "删除中..." : "确认删除"}
            </button>
            <button
              onClick={() => setConfirmDelete(false)}
              className="text-sm text-gray-500 hover:text-gray-700"
            >
              取消
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
