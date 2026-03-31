"use client";

import { useState } from "react";
import { api, ApiClientError } from "@/lib/api";
import { showErrorToast } from "@/components/error-toast";

interface NodeMergeModalProps {
  projectId: string;
  selectedNodes: Array<{ id: string; name: string }>;
  onClose: () => void;
  onSuccess: () => void;
}

export function NodeMergeModal({ projectId, selectedNodes, onClose, onSuccess }: NodeMergeModalProps) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [loading, setLoading] = useState(false);

  const handleMerge = async () => {
    if (!name.trim()) return;
    setLoading(true);
    try {
      await api.post(`/v1/projects/${projectId}/graph/nodes/merge`, {
        source_node_ids: selectedNodes.map((n) => n.id),
        target_name: name.trim(),
        target_description: description.trim() || null,
        target_node_type: "topic",
      });
      showErrorToast(`已将 ${selectedNodes.length} 个分类合并为"${name.trim()}"`, "info");
      onSuccess();
    } catch (e) {
      showErrorToast(e instanceof ApiClientError ? e.message : "合并失败");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl">
        <h3 className="mb-4 text-lg font-semibold text-gray-900">合并分类节点</h3>

        <div className="mb-4">
          <p className="mb-2 text-sm text-gray-500">将以下分类合并为一个新分类：</p>
          <ul className="space-y-1">
            {selectedNodes.map((n) => (
              <li key={n.id} className="rounded bg-gray-50 px-3 py-1.5 text-sm text-gray-700">
                {n.name}
              </li>
            ))}
          </ul>
        </div>

        <div className="mb-3">
          <label className="mb-1 block text-sm font-medium text-gray-700">新分类名称</label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="输入合并后的分类名称"
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
            autoFocus
          />
        </div>

        <div className="mb-4">
          <label className="mb-1 block text-sm font-medium text-gray-700">描述（可选）</label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="描述新分类的用途"
            rows={2}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
          />
        </div>

        <div className="flex justify-end gap-2">
          <button
            onClick={onClose}
            className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
          >
            取消
          </button>
          <button
            onClick={handleMerge}
            disabled={!name.trim() || loading}
            className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
          >
            {loading ? "合并中..." : "确认合并"}
          </button>
        </div>
      </div>
    </div>
  );
}
