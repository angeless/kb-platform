"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { api, ApiClientError } from "@/lib/api";
import { PermissionGuard } from "@/components/PermissionGuard";

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

interface StageConfig {
  stage_name: string;
  enabled: boolean;
  params: Record<string, unknown>;
}

const STAGE_LABELS: Record<string, { label: string; desc: string }> = {
  classify: { label: "内容分类", desc: "将原始片段分类为新增/补充/修正/冲突" },
  architecture_draft: { label: "架构生成", desc: "AI 自动生成知识体系架构" },
  doc_generate: { label: "文档生成", desc: "AI 将片段整合为结构化知识文档" },
  quality_check: { label: "质量检查", desc: "校验生成内容的基本质量" },
  conflict_detect: { label: "冲突检测", desc: "检测跨文档的内容冲突" },
  embed: { label: "向量嵌入", desc: "生成语义向量用于检索" },
  review_notify: { label: "审核通知", desc: "通知审核者新生成的内容" },
};

const CORE_STAGES = new Set(["doc_generate", "embed"]);

type TabKey = "general" | "pipeline";

export default function ProjectSettingsPage() {
  const params = useParams();
  const router = useRouter();
  const projectId = params.id as string;

  const [activeTab, setActiveTab] = useState<TabKey>("general");
  const [project, setProject] = useState<Project | null>(null);
  const [name, setName] = useState("");
  const [industry, setIndustry] = useState("");
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  // Pipeline config state
  const [stages, setStages] = useState<StageConfig[]>([]);
  const [pipelineLoading, setPipelineLoading] = useState(false);
  const [pipelineSaving, setPipelineSaving] = useState(false);
  const [entityInput, setEntityInput] = useState("");

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

  const fetchPipelineConfig = useCallback(async () => {
    setPipelineLoading(true);
    try {
      const resp = await api.get<{ stages: StageConfig[] }>(
        `/v1/projects/${projectId}/pipeline-config`,
      );
      setStages(resp.data.stages);
    } catch (e) {
      console.error("Failed to load pipeline config", e);
    } finally {
      setPipelineLoading(false);
    }
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
    fetchPipelineConfig();
  }, [projectId, fetchApiKeys, fetchPipelineConfig]);

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

  // --- Pipeline config helpers ---
  const updateStage = (stageName: string, patch: Partial<StageConfig>) => {
    setStages((prev) =>
      prev.map((s) => (s.stage_name === stageName ? { ...s, ...patch } : s)),
    );
  };

  const updateStageParam = (stageName: string, key: string, value: unknown) => {
    setStages((prev) =>
      prev.map((s) =>
        s.stage_name === stageName
          ? { ...s, params: { ...s.params, [key]: value } }
          : s,
      ),
    );
  };

  const handleSavePipeline = async () => {
    setPipelineSaving(true);
    setMessage("");
    setError("");
    try {
      const results = await Promise.allSettled(
        stages.map((stage) =>
          api.put(`/v1/projects/${projectId}/pipeline-config/${stage.stage_name}`, {
            enabled: stage.enabled,
            params: stage.params,
          }),
        ),
      );
      const failed = results
        .map((r, i) => (r.status === "rejected" ? stages[i].stage_name : null))
        .filter(Boolean);
      if (failed.length > 0) {
        setError(`部分 stage 保存失败: ${failed.join(", ")}`);
      } else {
        setMessage("知识提取配置已保存");
      }
    } catch (e) {
      setError(e instanceof ApiClientError ? e.message : "保存配置失败");
    } finally {
      setPipelineSaving(false);
    }
  };

  const [resetting, setResetting] = useState(false);

  const handleResetPipeline = async () => {
    if (resetting) return;
    setResetting(true);
    setMessage("");
    setError("");
    try {
      await api.post(`/v1/projects/${projectId}/pipeline-config/reset`, {});
      await fetchPipelineConfig();
      setMessage("已重置为默认配置");
    } catch (e) {
      setError(e instanceof ApiClientError ? e.message : "重置失败");
    } finally {
      setResetting(false);
    }
  };

  const addEntityType = (stageName: string) => {
    const val = entityInput.trim();
    if (!val) return;
    const stage = stages.find((s) => s.stage_name === stageName);
    if (!stage) return;
    const existing = (stage.params.entity_types as string[] | undefined) || [];
    if (existing.includes(val)) return;
    updateStageParam(stageName, "entity_types", [...existing, val]);
    setEntityInput("");
  };

  const removeEntityType = (stageName: string, tag: string) => {
    const stage = stages.find((s) => s.stage_name === stageName);
    if (!stage) return;
    const existing = (stage.params.entity_types as string[] | undefined) || [];
    updateStageParam(
      stageName,
      "entity_types",
      existing.filter((t) => t !== tag),
    );
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

      {/* Tab switcher */}
      <div className="mb-6 flex gap-1 rounded-lg bg-gray-100 p-1">
        {[
          { key: "general" as TabKey, label: "基本设置" },
          { key: "pipeline" as TabKey, label: "知识提取配置" },
        ].map((tab) => (
          <button
            key={tab.key}
            onClick={() => { setActiveTab(tab.key); setMessage(""); setError(""); }}
            className={`flex-1 rounded-md px-4 py-2 text-sm font-medium transition-colors ${
              activeTab === tab.key
                ? "bg-white text-gray-900 shadow-sm"
                : "text-gray-500 hover:text-gray-700"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {message && (
        <div className="mb-4 rounded-lg bg-green-50 p-3 text-sm text-green-600">{message}</div>
      )}
      {error && (
        <div className="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-600">{error}</div>
      )}

      {activeTab === "general" && (<>
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
          <PermissionGuard action="manage_project">
            <button
              type="submit"
              disabled={saving}
              className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
            >
              {saving ? "保存中..." : "保存"}
            </button>
          </PermissionGuard>
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
          <PermissionGuard action="manage_project">
            <button
              onClick={handleCreateKey}
              disabled={creatingKey || !newKeyName.trim()}
              className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
            >
              {creatingKey ? "创建中..." : "创建 Key"}
            </button>
          </PermissionGuard>
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
                    <PermissionGuard action="manage_project">
                      {revokeId === k.id ? (
                        <span className="flex items-center gap-1">
                          <button onClick={() => handleRevokeKey(k.id)} className="text-red-600 hover:underline">确认撤销</button>
                          <button onClick={() => setRevokeId(null)} className="text-gray-500 hover:underline">取消</button>
                        </span>
                      ) : (
                        <button onClick={() => setRevokeId(k.id)} className="text-red-500 hover:underline">撤销</button>
                      )}
                    </PermissionGuard>
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
      <PermissionGuard action="delete_project">
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
      </PermissionGuard>
      </>)}

      {activeTab === "pipeline" && (
        <PermissionGuard action="manage_project">
        <div className="space-y-4">
          {pipelineLoading ? (
            <div className="py-8 text-center text-gray-400">加载配置中...</div>
          ) : (
            <>
              {stages.map((stage) => {
                const meta = STAGE_LABELS[stage.stage_name];
                const isCore = CORE_STAGES.has(stage.stage_name);
                return (
                  <div
                    key={stage.stage_name}
                    className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm"
                  >
                    {/* Header: label + toggle */}
                    <div className="mb-2 flex items-center justify-between">
                      <div>
                        <span className="text-sm font-semibold text-gray-900">
                          {meta?.label ?? stage.stage_name}
                        </span>
                        {isCore && (
                          <span className="ml-2 rounded bg-amber-100 px-1.5 py-0.5 text-xs text-amber-700">
                            核心
                          </span>
                        )}
                        <p className="mt-0.5 text-xs text-gray-500">{meta?.desc}</p>
                      </div>
                      <label className="relative inline-flex cursor-pointer items-center">
                        <input
                          type="checkbox"
                          checked={stage.enabled}
                          onChange={(e) => updateStage(stage.stage_name, { enabled: e.target.checked })}
                          className="peer sr-only"
                        />
                        <div className="h-6 w-11 rounded-full bg-gray-200 after:absolute after:left-[2px] after:top-[2px] after:h-5 after:w-5 after:rounded-full after:bg-white after:transition-all peer-checked:bg-primary-600 peer-checked:after:translate-x-full" />
                      </label>
                    </div>

                    {/* Stage-specific params */}
                    {stage.stage_name === "classify" && stage.enabled && (
                      <div className="mt-3 space-y-3 border-t border-gray-100 pt-3">
                        <div>
                          <label className="mb-1 block text-xs font-medium text-gray-600">
                            置信度阈值: {Number(stage.params.confidence_threshold ?? 0.7).toFixed(2)}
                          </label>
                          <input
                            type="range"
                            min={0}
                            max={1}
                            step={0.05}
                            value={Number(stage.params.confidence_threshold ?? 0.7)}
                            onChange={(e) =>
                              updateStageParam(stage.stage_name, "confidence_threshold", parseFloat(e.target.value))
                            }
                            className="w-full accent-primary-600"
                          />
                        </div>
                        <div>
                          <label className="mb-1 block text-xs font-medium text-gray-600">
                            自定义实体类型
                          </label>
                          <div className="mb-2 flex flex-wrap gap-1.5">
                            {((stage.params.entity_types as string[] | undefined) || []).map((tag) => (
                              <span
                                key={tag}
                                className="inline-flex items-center gap-1 rounded-full bg-primary-50 px-2.5 py-1 text-xs text-primary-700"
                              >
                                {tag}
                                <button
                                  onClick={() => removeEntityType(stage.stage_name, tag)}
                                  className="text-primary-400 hover:text-primary-600"
                                >
                                  ×
                                </button>
                              </span>
                            ))}
                          </div>
                          <div className="flex gap-2">
                            <input
                              type="text"
                              value={entityInput}
                              onChange={(e) => setEntityInput(e.target.value)}
                              onKeyDown={(e) => {
                                if (e.key === "Enter") { e.preventDefault(); addEntityType(stage.stage_name); }
                              }}
                              placeholder="输入实体类型，回车添加"
                              className="flex-1 rounded-lg border border-gray-300 px-3 py-1.5 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                            />
                            <button
                              onClick={() => addEntityType(stage.stage_name)}
                              className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-50"
                            >
                              添加
                            </button>
                          </div>
                        </div>
                      </div>
                    )}

                    {stage.stage_name === "quality_check" && stage.enabled && (
                      <div className="mt-3 space-y-3 border-t border-gray-100 pt-3">
                        <div>
                          <label className="mb-1 block text-xs font-medium text-gray-600">
                            最小内容长度
                          </label>
                          <input
                            type="number"
                            min={0}
                            max={1000}
                            value={Number(stage.params.min_content_length ?? 50)}
                            onChange={(e) =>
                              updateStageParam(stage.stage_name, "min_content_length", parseInt(e.target.value) || 0)
                            }
                            className="w-32 rounded-lg border border-gray-300 px-3 py-1.5 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                          />
                        </div>
                        <label className="flex items-center gap-2 text-sm text-gray-700">
                          <input
                            type="checkbox"
                            checked={stage.params.require_title !== false}
                            onChange={(e) =>
                              updateStageParam(stage.stage_name, "require_title", e.target.checked)
                            }
                            className="h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                          />
                          要求标题
                        </label>
                      </div>
                    )}

                    {stage.stage_name === "conflict_detect" && stage.enabled && (
                      <div className="mt-3 border-t border-gray-100 pt-3">
                        <label className="mb-1 block text-xs font-medium text-gray-600">
                          相似度阈值: {Number(stage.params.similarity_threshold ?? 0.85).toFixed(2)}
                        </label>
                        <input
                          type="range"
                          min={0}
                          max={1}
                          step={0.05}
                          value={Number(stage.params.similarity_threshold ?? 0.85)}
                          onChange={(e) =>
                            updateStageParam(stage.stage_name, "similarity_threshold", parseFloat(e.target.value))
                          }
                          className="w-full accent-primary-600"
                        />
                      </div>
                    )}
                  </div>
                );
              })}

              {/* Actions */}
              <div className="flex items-center justify-between pt-2">
                <button
                  onClick={handleResetPipeline}
                  disabled={resetting}
                  className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-600 hover:bg-gray-50 disabled:opacity-50"
                >
                  {resetting ? "重置中..." : "重置为默认"}
                </button>
                <button
                  onClick={handleSavePipeline}
                  disabled={pipelineSaving}
                  className="rounded-lg bg-primary-600 px-5 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
                >
                  {pipelineSaving ? "保存中..." : "保存配置"}
                </button>
              </div>
            </>
          )}
        </div>
        </PermissionGuard>
      )}
    </div>
  );
}
