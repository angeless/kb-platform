"use client";

import { useCallback, useRef, useState } from "react";
import { ApiClientError, uploadWithProgress } from "@/lib/api";

interface FileUploadProps {
  projectId: string;
  onUploadComplete: () => void;
}

interface UploadItem {
  file: File;
  status: "pending" | "uploading" | "done" | "error" | "cancelled";
  progress: number;
  message?: string;
}

// M-02 fix: allowed file types and max size
const ALLOWED_EXTENSIONS = new Set([
  "pdf", "txt", "md", "docx", "doc", "csv", "json", "html", "xml",
  "zip", "rar", "7z", "tar",
  "png", "jpg", "jpeg", "gif", "webp",
  "mp3", "wav", "m4a", "flac",
  "mp4", "avi", "mov",
]);
const MAX_UPLOAD_SIZE_MB = 100;
const MAX_UPLOAD_SIZE_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024;

function validateFile(file: File): string | null {
  const ext = file.name.split(".").pop()?.toLowerCase() || "";
  if (!ALLOWED_EXTENSIONS.has(ext)) {
    return `不支持的文件类型: .${ext}`;
  }
  if (file.size > MAX_UPLOAD_SIZE_BYTES) {
    return `文件大小超出限制 (${MAX_UPLOAD_SIZE_MB}MB)`;
  }
  return null;
}

export function FileUpload({ projectId, onUploadComplete }: FileUploadProps) {
  const [items, setItems] = useState<UploadItem[]>([]);
  const [isDragOver, setIsDragOver] = useState(false);
  const abortControllers = useRef<Map<number, AbortController>>(new Map());

  const updateItem = (index: number, update: Partial<UploadItem>) => {
    setItems((prev) =>
      prev.map((item, i) => (i === index ? { ...item, ...update } : item)),
    );
  };

  const uploadFile = async (file: File, index: number) => {
    const controller = new AbortController();
    abortControllers.current.set(index, controller);

    updateItem(index, { status: "uploading", progress: 0 });

    const formData = new FormData();
    formData.append("file", file);
    formData.append("project_id", projectId);
    formData.append("asset_type", guessType(file.name));

    try {
      await uploadWithProgress("/v1/assets/upload", formData, {
        onProgress: (percent) => updateItem(index, { progress: percent }),
        signal: controller.signal,
      });
      updateItem(index, { status: "done", progress: 100 });
    } catch (e) {
      if (e instanceof ApiClientError && e.errorCode === "UPLOAD_CANCELLED") {
        updateItem(index, { status: "cancelled", message: "已取消" });
      } else {
        const msg = e instanceof ApiClientError ? e.message : "上传失败";
        updateItem(index, { status: "error", message: msg });
      }
    } finally {
      abortControllers.current.delete(index);
    }
  };

  const cancelUpload = (index: number) => {
    const controller = abortControllers.current.get(index);
    if (controller) {
      controller.abort();
    }
  };

  const handleFiles = useCallback(
    async (files: FileList | File[]) => {
      const newItems: UploadItem[] = Array.from(files).map((file) => {
        const error = validateFile(file);
        return {
          file,
          status: error ? ("error" as const) : ("pending" as const),
          progress: 0,
          message: error || undefined,
        };
      });
      setItems((prev) => [...prev, ...newItems]);

      const startIndex = items.length;
      for (let i = 0; i < newItems.length; i++) {
        if (newItems[i].status === "error") continue;
        await uploadFile(newItems[i].file, startIndex + i);
      }
      onUploadComplete();
    },
    [items.length, projectId, onUploadComplete],
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragOver(false);
      if (e.dataTransfer.files.length > 0) {
        handleFiles(e.dataTransfer.files);
      }
    },
    [handleFiles],
  );

  return (
    <div className="space-y-3">
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
        <p className="mb-2 text-sm text-gray-500">拖拽文件到此处，或</p>
        <label className="cursor-pointer rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700">
          选择文件
          <input
            type="file"
            multiple
            className="hidden"
            onChange={(e) => {
              if (e.target.files) handleFiles(e.target.files);
            }}
          />
        </label>
        <p className="mt-2 text-xs text-gray-400">
          支持 PDF、图片、音频、文本、Word、压缩包等格式
        </p>
      </div>

      {items.length > 0 && (
        <ul className="space-y-2">
          {items.map((item, i) => (
            <li key={i} className="rounded-lg bg-white px-3 py-2 text-sm">
              <div className="flex items-center justify-between">
                <span className="truncate text-gray-700">{item.file.name}</span>
                <div className="flex items-center gap-2">
                  {item.status === "uploading" && (
                    <>
                      <span className="text-primary-600">{item.progress}%</span>
                      <button
                        onClick={() => cancelUpload(i)}
                        className="text-xs text-gray-400 hover:text-red-500"
                        title="取消上传"
                      >
                        ✕
                      </button>
                    </>
                  )}
                  {item.status === "done" && (
                    <span className="text-green-600">✓ 完成</span>
                  )}
                  {item.status === "error" && (
                    <span className="text-red-500">✕ {item.message || "失败"}</span>
                  )}
                  {item.status === "cancelled" && (
                    <span className="text-gray-400">已取消</span>
                  )}
                  {item.status === "pending" && (
                    <span className="text-gray-400">等待中</span>
                  )}
                </div>
              </div>
              {item.status === "uploading" && (
                <div className="mt-1.5 h-1.5 w-full overflow-hidden rounded-full bg-gray-200">
                  <div
                    className="h-full rounded-full bg-primary-500 transition-all duration-300"
                    style={{ width: `${item.progress}%` }}
                  />
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function guessType(filename: string): string {
  const ext = filename.split(".").pop()?.toLowerCase() || "";
  const map: Record<string, string> = {
    pdf: "pdf",
    png: "image", jpg: "image", jpeg: "image", gif: "image", webp: "image",
    mp3: "audio", wav: "audio", m4a: "audio", flac: "audio",
    mp4: "video", avi: "video", mov: "video",
    zip: "zip", rar: "zip", "7z": "zip", tar: "zip",
    doc: "doc", docx: "doc",
    txt: "text", md: "text", csv: "text",
  };
  return map[ext] || "document";
}
