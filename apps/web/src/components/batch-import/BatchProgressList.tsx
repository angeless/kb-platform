"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { StatusBadge } from "@/components/status-badge";

interface BatchFile {
  asset_id: string;
  original_filename: string;
  parse_status: string;
}

interface BatchStatus {
  batch_id: string;
  status: string;
  total_files: number;
  completed_files: number;
  failed_files: number;
  files: BatchFile[];
}

interface BatchProgressListProps {
  projectId: string;
  batchId: string;
  onComplete: () => void;
}

export function BatchProgressList({ projectId, batchId, onComplete }: BatchProgressListProps) {
  const [batch, setBatch] = useState<BatchStatus | null>(null);
  const [error, setError] = useState("");
  const onCompleteRef = useRef(onComplete);
  onCompleteRef.current = onComplete;
  const doneRef = useRef(false);

  const fetchStatus = useCallback(async () => {
    if (doneRef.current) return;
    try {
      const resp = await api.get<BatchStatus>(
        `/v1/projects/${projectId}/batch-import/${batchId}`,
      );
      setBatch(resp.data);
      if (resp.data.status === "completed" || resp.data.status === "partial_failed") {
        doneRef.current = true;
        onCompleteRef.current();
      }
    } catch {
      setError("获取批次状态失败");
    }
  }, [projectId, batchId]);

  useEffect(() => {
    doneRef.current = false;
    fetchStatus();
    const interval = setInterval(fetchStatus, 3000);
    return () => clearInterval(interval);
  }, [fetchStatus]);

  if (error) return <div className="text-sm text-red-500">{error}</div>;
  if (!batch) return <div className="text-sm text-gray-400">加载中...</div>;

  const isDone = batch.status === "completed" || batch.status === "partial_failed";

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
      {/* Summary */}
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="text-sm font-semibold text-gray-900">
            批量导入
          </span>
          <StatusBadge status={batch.status} />
        </div>
        <span className="text-xs text-gray-400">
          {batch.completed_files + batch.failed_files} / {batch.total_files} 完成
        </span>
      </div>

      {/* Progress bar */}
      <div className="mb-3 h-2 overflow-hidden rounded-full bg-gray-200">
        <div
          className="h-full rounded-full bg-primary-500 transition-all"
          style={{
            width: `${batch.total_files > 0 ? ((batch.completed_files + batch.failed_files) / batch.total_files) * 100 : 0}%`,
          }}
        />
      </div>

      {/* File list */}
      <div className="max-h-60 overflow-y-auto">
        <ul className="divide-y divide-gray-100 text-sm">
          {batch.files.map((f) => (
            <li key={f.asset_id} className="flex items-center justify-between py-2">
              <span className="truncate text-gray-700" title={f.original_filename}>
                {f.original_filename}
              </span>
              <StatusBadge status={f.parse_status} />
            </li>
          ))}
        </ul>
      </div>

      {/* Done summary */}
      {isDone && (
        <div className={`mt-3 rounded-lg p-2 text-center text-sm ${batch.failed_files > 0 ? "bg-yellow-50 text-yellow-700" : "bg-green-50 text-green-700"}`}>
          {batch.failed_files > 0
            ? `完成 ${batch.completed_files} 个，失败 ${batch.failed_files} 个`
            : `全部 ${batch.completed_files} 个文件处理完成`}
        </div>
      )}
    </div>
  );
}
