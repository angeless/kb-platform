"use client";

import { useCallback, useEffect, useState } from "react";
import { api, ApiClientError } from "@/lib/api";
import { PermissionGuard } from "@/components/PermissionGuard";
import { VersionDiff } from "./VersionDiff";
import { RollbackConfirm } from "./RollbackConfirm";

interface VersionSummary {
  version: number;
  change_reason: string | null;
  created_by: string;
  created_at: string;
}

interface VersionListData {
  versions: VersionSummary[];
  total: number;
  current_version: number;
}

interface VersionPanelProps {
  docId: string;
  currentVersion: number;
  onClose: () => void;
  onRollbackSuccess: () => void;
}

export function VersionPanel({ docId, currentVersion, onClose, onRollbackSuccess }: VersionPanelProps) {
  const [versions, setVersions] = useState<VersionSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selectedVersion, setSelectedVersion] = useState<number | null>(null);
  const [rollbackTarget, setRollbackTarget] = useState<number | null>(null);
  const [rollbackLoading, setRollbackLoading] = useState(false);

  const fetchVersions = useCallback(async () => {
    setLoading(true);
    try {
      const resp = await api.get<VersionListData>(`/v1/docs/${docId}/versions`);
      setVersions(resp.data.versions);
    } catch (e) {
      setError(e instanceof ApiClientError ? e.message : "加载版本列表失败");
    } finally {
      setLoading(false);
    }
  }, [docId]);

  useEffect(() => {
    fetchVersions();
  }, [fetchVersions]);

  const handleRollback = async () => {
    if (rollbackTarget === null) return;
    setRollbackLoading(true);
    try {
      await api.post(`/v1/docs/${docId}/versions/${rollbackTarget}/rollback`, {});
      setRollbackTarget(null);
      onRollbackSuccess();
    } catch (e) {
      setError(e instanceof ApiClientError ? e.message : "回滚失败");
      setRollbackLoading(false);
    }
  };

  return (
    <>
      <div className="flex h-full flex-col border-l border-gray-200 bg-white">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-gray-200 px-4 py-3">
          <h3 className="text-sm font-semibold text-gray-900">历史版本</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            &times;
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto">
          {loading ? (
            <div className="py-8 text-center text-sm text-gray-400">加载中...</div>
          ) : error ? (
            <div className="px-4 py-4 text-sm text-red-500">{error}</div>
          ) : versions.length === 0 ? (
            <div className="py-8 text-center text-sm text-gray-400">暂无版本记录</div>
          ) : (
            <div>
              {/* Version list */}
              <ul className="divide-y divide-gray-100">
                {versions.map((v) => {
                  const isCurrent = v.version === currentVersion;
                  const isSelected = v.version === selectedVersion;
                  return (
                    <li key={v.version}>
                      <button
                        onClick={() => setSelectedVersion(isSelected ? null : v.version)}
                        className={`w-full px-4 py-3 text-left transition-colors ${
                          isSelected ? "bg-primary-50" : "hover:bg-gray-50"
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <span className="text-sm font-medium text-gray-900">
                            v{v.version}
                            {isCurrent && (
                              <span className="ml-1.5 rounded bg-primary-100 px-1.5 py-0.5 text-xs text-primary-700">
                                当前
                              </span>
                            )}
                          </span>
                          <span className="text-xs text-gray-400">
                            {new Date(v.created_at).toLocaleDateString()}
                          </span>
                        </div>
                        {v.change_reason && (
                          <p className="mt-1 text-xs text-gray-500">{v.change_reason}</p>
                        )}
                      </button>

                      {/* Expanded: Diff + Rollback */}
                      {isSelected && !isCurrent && (
                        <div className="border-t border-gray-100 bg-gray-50 px-4 py-3">
                          <VersionDiff
                            docId={docId}
                            fromVersion={v.version}
                            toVersion={currentVersion}
                          />
                          <div className="mt-3">
                            <PermissionGuard action="edit">
                              <button
                                onClick={() => setRollbackTarget(v.version)}
                                className="rounded-lg bg-primary-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-primary-700"
                              >
                                回滚到此版本
                              </button>
                            </PermissionGuard>
                          </div>
                        </div>
                      )}
                    </li>
                  );
                })}
              </ul>
            </div>
          )}
        </div>
      </div>

      {/* Rollback Confirmation Modal */}
      {rollbackTarget !== null && (
        <RollbackConfirm
          version={rollbackTarget}
          onConfirm={handleRollback}
          onCancel={() => setRollbackTarget(null)}
          loading={rollbackLoading}
        />
      )}
    </>
  );
}
