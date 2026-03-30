"use client";

import { useCallback, useRef, useState } from "react";
import { ApiClientError, uploadWithProgress } from "@/lib/api";

interface BatchDropzoneProps {
  projectId: string;
  onBatchCreated: (batchId: string) => void;
}

type Phase = "idle" | "uploading" | "done" | "error";

export function BatchDropzone({ projectId, onBatchCreated }: BatchDropzoneProps) {
  const [phase, setPhase] = useState<Phase>("idle");
  const [progress, setProgress] = useState(0);
  const [errorMsg, setErrorMsg] = useState("");
  const [isDragOver, setIsDragOver] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  const validateZip = useCallback((file: File): string | null => {
    const ext = file.name.split(".").pop()?.toLowerCase();
    if (ext !== "zip") {
      return "请上传 .zip 格式文件";
    }
    if (file.size > 500 * 1024 * 1024) {
      return "ZIP 文件大小不能超过 500MB";
    }
    return null;
  }, []);

  const upload = useCallback(
    async (file: File) => {
      const err = validateZip(file);
      if (err) {
        setErrorMsg(err);
        setPhase("error");
        return;
      }

      setPhase("uploading");
      setProgress(0);
      setErrorMsg("");

      const controller = new AbortController();
      abortRef.current = controller;

      const formData = new FormData();
      formData.append("file", file);
      formData.append("auto_start", "true");

      try {
        const resp = await uploadWithProgress(
          `/v1/projects/${projectId}/batch-import`,
          formData,
          {
            onProgress: (pct) => setProgress(pct),
            signal: controller.signal,
          },
        );
        const batchId = (resp.data as { batch_id: string }).batch_id;
        setPhase("done");
        onBatchCreated(batchId);
      } catch (e) {
        if (e instanceof ApiClientError && e.errorCode === "UPLOAD_CANCELLED") {
          setPhase("idle");
        } else {
          setErrorMsg(e instanceof ApiClientError ? e.message : "上传失败");
          setPhase("error");
        }
      } finally {
        abortRef.current = null;
      }
    },
    [projectId, validateZip, onBatchCreated],
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragOver(false);
      const file = e.dataTransfer.files[0];
      if (file) upload(file);
    },
    [upload],
  );

  const cancel = () => {
    abortRef.current?.abort();
  };

  if (phase === "uploading") {
    return (
      <div className="rounded-xl border border-gray-200 bg-white p-6">
        <div className="mb-2 flex items-center justify-between text-sm">
          <span className="text-gray-700">正在上传 ZIP...</span>
          <div className="flex items-center gap-3">
            <span className="font-medium text-primary-600">{progress}%</span>
            <button
              onClick={cancel}
              className="text-xs text-gray-400 hover:text-red-500"
            >
              取消
            </button>
          </div>
        </div>
        <div className="h-2 overflow-hidden rounded-full bg-gray-200">
          <div
            className="h-full rounded-full bg-primary-500 transition-all duration-300"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>
    );
  }

  if (phase === "done") {
    return null;
  }

  return (
    <div className="space-y-2">
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragOver(true);
        }}
        onDragLeave={() => setIsDragOver(false)}
        onDrop={handleDrop}
        className={`flex flex-col items-center justify-center rounded-xl border-2 border-dashed p-8 transition-colors ${
          isDragOver
            ? "border-primary-400 bg-primary-50"
            : "border-gray-300 bg-gray-50 hover:border-gray-400"
        }`}
      >
        <p className="mb-2 text-sm text-gray-500">
          拖拽 ZIP 文件到此处，或
        </p>
        <label className="cursor-pointer rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700">
          选择 ZIP 文件
          <input
            type="file"
            accept=".zip"
            className="hidden"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) upload(file);
              e.target.value = "";
            }}
          />
        </label>
        <p className="mt-2 text-xs text-gray-400">
          仅支持 .zip 格式，最大 500MB
        </p>
      </div>

      {phase === "error" && errorMsg && (
        <div className="rounded-lg bg-red-50 p-3 text-center text-sm text-red-600">
          {errorMsg}
        </div>
      )}
    </div>
  );
}
