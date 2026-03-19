"use client";

import { useState } from "react";
import { api, ApiClientError } from "@/lib/api";
import { StatusBadge } from "@/components/status-badge";
import type { TreeNodeData } from "@/components/tree-node";

interface NodePanelProps {
  node: TreeNodeData;
  archId: string;
  onClose: () => void;
  onUpdated: () => void;
}

export function NodePanel({ node, archId, onClose, onUpdated }: NodePanelProps) {
  const [name, setName] = useState(node.node_name);
  const [description, setDescription] = useState(node.description || "");
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");

  const handleSave = async () => {
    setSaving(true);
    setMessage("");
    try {
      await api.patch(`/v1/architectures/${archId}/nodes/${node.id}`, {
        node_name: name,
        description: description || null,
      });
      setMessage("已保存");
      onUpdated();
    } catch (e) {
      setMessage(e instanceof ApiClientError ? e.message : "保存失败");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="border-l border-gray-200 bg-white p-5">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-lg font-semibold text-gray-900">节点详情</h3>
        <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
          ✕
        </button>
      </div>

      <div className="mb-4 flex items-center gap-2">
        <StatusBadge status={node.status} />
        <span className="text-sm text-gray-500">类型：{node.node_type}</span>
        <span className="text-sm text-gray-500">层级：{node.level}</span>
      </div>

      {message && (
        <div className={`mb-3 rounded-lg p-2 text-sm ${
          message === "已保存" ? "bg-green-50 text-green-600" : "bg-red-50 text-red-600"
        }`}>
          {message}
        </div>
      )}

      <div className="space-y-4">
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">名称</label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
          />
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">描述</label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={4}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
          />
        </div>
        <button
          onClick={handleSave}
          disabled={saving}
          className="w-full rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
        >
          {saving ? "保存中..." : "保存修改"}
        </button>
      </div>
    </div>
  );
}
